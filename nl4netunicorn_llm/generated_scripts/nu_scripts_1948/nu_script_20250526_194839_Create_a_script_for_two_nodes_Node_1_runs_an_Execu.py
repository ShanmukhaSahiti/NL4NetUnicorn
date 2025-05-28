from netunicorn.client.remote import RemoteClient, RemoteClientException
from netunicorn.base.pipeline import Pipeline
from netunicorn.library.tasks.data_transfer import SendData, FetchData
from netunicorn.library.tasks.shell import ExecuteShellCommand
from netunicorn.base.experiment import Experiment, ExperimentStatus
from netunicorn.base.environment_definitions import ShellExecution
from netunicorn.base.nodes import NodePool
import time

# Credentials
endpoint = "https://pinot.cs.ucsb.edu/netunicorn"
login = "293nmay25"
password = "4Ij9Du65jrqj"

# Client Initialization
client = RemoteClient(endpoint=endpoint, login=login, password=password)

# Pipeline Creation
pipeline = Pipeline()

# Node Selection
node_pool = client.get_nodes()
working_nodes = node_pool.take(2)  # Select two nodes

# Experiment object creation
experiment = Experiment()

# Environment definition
experiment.environment_definition = ShellExecution()

# Experiment mapping
experiment.map(pipeline, working_nodes)

# Experiment name
experiment_name = "my_experiment_{timestamp}"  # Unique experiment name

# Delete old experiment
try:
    client.delete_experiment(experiment_name)
    print(f"Successfully deleted pre-existing experiment: {experiment_name}")
except RemoteClientException as e:
    print(f"Info: Could not delete experiment {experiment_name} (may not exist or already deleted): {e}")
except Exception as e:  # Catch any other potential exceptions during deletion
    print(f"Warning: An unexpected error occurred while trying to delete experiment {experiment_name}: {e}")

# Add tasks to the pipeline
pipeline.then(ExecuteShellCommand("echo 'Hello NetUnicorn' > mydata.txt"))  # Node 1 creates 'mydata.txt'
pipeline.then(SendData("mydata.txt", "send_data_task", data_type="file"))  # Node 1 makes 'mydata.txt' available

# Fetch 'mydata.txt' on Node 2 and print its content
pipeline.then(FetchData("send_data_task", working_nodes[1].name))  # Node 2 fetches 'mydata.txt'
pipeline.then(ExecuteShellCommand("cat mydata.txt"))  # Node 2 prints the content of 'mydata.txt'

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
    time.sleep(10)  # Poll every 10 seconds

# Start experiment
client.start_execution(experiment_name)
print(f"Experiment {experiment_name} started. Waiting for completion...")

# Poll for FINISHED
while True:
    status = client.get_experiment_status(experiment_name).status
    print(f"Current status: {status}")
    if status != ExperimentStatus.RUNNING:
        break
    time.sleep(20)  # Poll every 20 seconds

# Get and print results
final_status_info = client.get_experiment_status(experiment_name)
if final_status_info.status == ExperimentStatus.FINISHED:
    results = final_status_info.execution_result
    print(f"Experiment results: {results}")
    if results:
        for report_list in results:
            for report in report_list:
                if report:  # Report can be None if a node fails
                    print(f"Node: {report.node.name}, Success: {report.success}, Log: {report.log}")
                    if not report.success:
                        print(f"Error details: {report.error}")
else:
    print(f"Experiment did not finish successfully. Final status: {final_status_info.status}")
    if final_status_info.error:
        print(f"Error: {final_status_info.error}")