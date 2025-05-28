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
node1_command = ExecuteShellCommand("echo 'Hello NetUnicorn' > mydata.txt")
node1_send_data = SendData("mydata.txt", "mydata_task", data_type="file")
node2_fetch_data = FetchData("mydata_task", "Node1")
node2_command = ExecuteShellCommand("cat mydata.txt")

pipeline.then(node1_command).then(node1_send_data).then(node2_fetch_data).then(node2_command)

# Node Selection
node_pool = client.get_nodes()
working_nodes = node_pool.take(2)

# Experiment Object and Definition
experiment = Experiment()
experiment.environment_definition = ShellExecution()
experiment.map(pipeline, working_nodes)

# Experiment Naming and Cleanup
experiment_name = "my_experiment_" + str(int(time.time()))
try:
    client.delete_experiment(experiment_name)
    print(f"Successfully deleted pre-existing experiment: {experiment_name}")
except RemoteClientException as e:
    print(f"Info: Could not delete experiment {experiment_name} (may not exist or already deleted): {e}")
except Exception as e:
    print(f"Warning: An unexpected error occurred while trying to delete experiment {experiment_name}: {e}")

# Prepare the experiment
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

# Start the experiment execution
client.start_execution(experiment_name)

# Wait for the experiment to complete
print(f"Experiment {experiment_name} started. Waiting for completion...")
while True:
    status = client.get_experiment_status(experiment_name).status
    print(f"Current status: {status}")
    if status != ExperimentStatus.RUNNING:
        break
    time.sleep(20)  # Poll every 20 seconds

# Retrieve and print results if FINISHED
final_status_info = client.get_experiment_status(experiment_name)
if final_status_info.status == ExperimentStatus.FINISHED:
    results = final_status_info.execution_result
    print(f"Experiment results: {results}")
    if results:
        for report in results:
            print(f"Node name: {report.node.name}")
            print(f"Error: {report.error}")

            result, log = report.result
            print(type(result))
            if isinstance(result, Result):
                data = result.unwrap() if is_successful(result) else result
                pprint(data)
else:
    print(f"Experiment did not finish successfully. Final status: {final_status_info.status}")
    if final_status_info.error:
        print(f"Error: {final_status_info.error}")