from netunicorn.client.remote import RemoteClient, RemoteClientException
from netunicorn.base.pipeline import Pipeline
from netunicorn.library.tasks.flags import GetFlagTask, SetFlagTask, CheckFreeSpace, GetKernelVersion
from netunicorn.base.experiment import Experiment, ExperimentStatus
import time

# Credentials
endpoint = "https://pinot.cs.ucsb.edu/netunicorn"
login = "293nmay25"
password = "4Ij9Du65jrqj"

# Client Initialization
client = RemoteClient(endpoint=endpoint, login=login, password=password)

# Pipeline Creation
pipeline = Pipeline()
pipeline.then(GetKernelVersion().then(SetFlagTask(name='kernel_version'))).then(CheckFreeSpace(path='/tmp').then(SetFlagTask(name='tmp_free_space')))

# Node Selection
node_pool = client.get_nodes()
working_nodes = node_pool.take(1)

# Experiment Object and Definition
experiment = Experiment()
experiment.environment_definition = ShellExecution()
experiment.map(pipeline, working_nodes)

# Experiment Naming and Cleanup
experiment_name = "nl4netunicorn_experiment_{timestamp}"
try:
    client.delete_experiment(experiment_name)
    print(f"Successfully deleted pre-existing experiment: {experiment_name}")
except RemoteClientException as e:
    print(f"Info: Could not delete experiment {experiment_name} (may not exist or already deleted): {e}")
except Exception as e:
    print(f"Warning: An unexpected error occurred while trying to delete experiment {experiment_name}: {e}")

# Prepare the experiment
client.prepare_experiment(experiment, experiment_name)

# Poll for READY status
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