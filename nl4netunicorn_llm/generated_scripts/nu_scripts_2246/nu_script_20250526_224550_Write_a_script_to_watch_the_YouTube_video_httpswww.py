from netunicorn.client.remote import RemoteClient, RemoteClientException
from netunicorn.base.pipeline import Pipeline
from netunicorn.library.tasks.video_watchers.youtube_watcher import WatchYouTubeVideo
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

# Pipeline
pipeline = Pipeline()
pipeline.then(WatchYouTubeVideo("https://www.youtube.com/watch?v=dQw4w9WgXcQ", duration=20))

# Get available nodes
node_pool = client.get_nodes()
working_nodes = node_pool.take(1)

# Experiment object creation
experiment = Experiment()

# Environment definition
experiment.environment_definition = ShellExecution()

# Experiment mapping
experiment.map(pipeline, working_nodes)

# Experiment name
experiment_name = "youtube_watch_experiment"

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
    time.sleep(10)  # Poll every 10 seconds

# Start experiment
client.start_execution(experiment_name)

# Poll for FINISHED
print(f"Experiment {experiment_name} started. Waiting for completion...")
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