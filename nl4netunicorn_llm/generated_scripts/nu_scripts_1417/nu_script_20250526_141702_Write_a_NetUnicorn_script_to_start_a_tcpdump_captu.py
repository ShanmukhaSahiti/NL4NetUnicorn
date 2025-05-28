from netunicorn.client.remote import RemoteClient, RemoteClientException
from netunicorn.base.pipeline import Pipeline
from netunicorn.library.tasks.capture import tcpdump
from netunicorn.library.tasks.data_transfer import SendData
from netunicorn.base.experiment import Experiment, ExperimentStatus
import time

# Credentials
endpoint = "https://pinot.cs.ucsb.edu/netunicorn"
login = "293nmay25"
password = "4Ij9Du65jrqj"

# Client
client = RemoteClient(endpoint=endpoint, login=login, password=password)

# Pipeline
pipeline = Pipeline()

# Nodes
node_pool = client.get_nodes()
working_nodes = node_pool.take(1)

# Experiment object creation
experiment = Experiment()

# Environment definition
experiment.environment_definition = ShellExecution()

# Experiment mapping
experiment.map(pipeline, working_nodes)

# Experiment name
experiment_name = "tcpdump_capture_experiment_{timestamp}"

# Delete old experiment
try:
    client.delete_experiment(experiment_name)
    print(f"Successfully deleted pre-existing experiment: {experiment_name}")
except RemoteClientException as e:
    print(f"Info: Could not delete experiment {experiment_name} (may not exist or already deleted): {e}")
except Exception as e:
    print(f"Warning: An unexpected error occurred while trying to delete experiment {experiment_name}: {e}")

# Prepare experiment
client.prepare_experiment(experiment, experiment_name)

# Poll for READY
print(f"Experiment {experiment_name} prepared. Waiting for readiness...")
while True:
    status = client.get_experiment_status(experiment_name).status
    print(f"Current status: {status}")
    if status == ExperimentStatus.READY:
        print("Experiment is READY.")
        break
    elif status == ExperimentStatus.FINISHED or status == ExperimentStatus.ERROR:
        print(f"Experiment entered {status} state before becoming READY. Aborting.")
        exit()
    time.sleep(10)

# Start experiment
client.start_execution(experiment_name)

# Poll for FINISHED
print(f"Experiment {experiment_name} started. Waiting for completion...")
while True:
    status = client.get_experiment_status(experiment_name).status
    print(f"Current status: {status}")
    if status == ExperimentStatus.FINISHED:
        print("Experiment FINISHED.")
        break
    elif status == ExperimentStatus.ERROR:
        print(f"Experiment entered ERROR state. Aborting wait. Check logs.")
        break
    time.sleep(20)

# Get and print results
final_status_info = client.get_experiment_status(experiment_name)
if final_status_info.status == ExperimentStatus.FINISHED:
    results = final_status_info.execution_result
    print(f"Experiment results: {results}")
    if results:
        for report_list in results:
            for report in report_list:
                if report:
                    print(f"Node: {report.node.name}, Success: {report.success}, Log: {report.log}")
                    if not report.success:
                        print(f"Error details: {report.error}")
else:
    print(f"Experiment did not finish successfully. Final status: {final_status_info.status}")
    if final_status_info.error:
        print(f"Error: {final_status_info.error}")

# Start tcpdump capture
capture_task = tcpdump.StartCapture(filepath="capture.pcap", arguments=["-w", "30"])
pipeline.then(capture_task)

# Stop tcpdump capture
stop_capture_task = tcpdump.StopNamedCapture(name=capture_task.name)
pipeline.then(stop_capture_task)

# SendData to make 'capture.pcap' available
send_data_task = SendData(filepath="capture.pcap", task_name=stop_capture_task.name, data_type="file")
pipeline.then(send_data_task)