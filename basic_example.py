import os
import time
from pprint import pprint

# Import netunicorn packages
from netunicorn.client.remote import RemoteClient, RemoteClientException
from netunicorn.base.experiment import Experiment, ExperimentStatus
from netunicorn.base.pipeline import Pipeline
from netunicorn.library.tasks.basic import SleepTask
from returns.pipeline import is_successful
from returns.result import Result

def main():
    # API connection parameters
    endpoint = 'https://pinot.cs.ucsb.edu/netunicorn'
    login = '293nmay25'
    password = '4Ij9Du65jrqj'

    # Create pipeline
    pipeline = Pipeline()
    pipeline = pipeline.then([
        SleepTask(5),
        SleepTask(3)
    ]).then(
        SleepTask(10)
    )

    # Create client and check health
    client = RemoteClient(endpoint=endpoint, login=login, password=password)
    print(f"Health check: {client.healthcheck()}")

    # Get available nodes
    nodes = client.get_nodes()
    print("\nAvailable nodes:")
    for element in nodes:
        print(element)

    # Select nodes for experiment
    interesting_nodes = nodes.filter(lambda node: node.name == 'snl-server-5')
    working_nodes = interesting_nodes.take(1)
    print("\nSelected nodes for experiment:")
    print(working_nodes)

    # Create and prepare experiment
    experiment = Experiment().map(pipeline, working_nodes)
    experiment_name = 'experiment_cool_name'

    # Clean up any existing experiment with the same name
    try:
        client.delete_experiment(experiment_name)
    except RemoteClientException:
        pass

    # Prepare the experiment
    client.prepare_experiment(experiment, experiment_name)

    # Wait for experiment to be ready
    print("\nWaiting for experiment to be ready...")
    while True:
        info = client.get_experiment_status(experiment_name)
        print(info.status)
        if info.status == ExperimentStatus.READY:
            break
        time.sleep(20)

    # Check deployment status
    prepared_experiment = info.experiment
    print("\nDeployment status:")
    for deployment in prepared_experiment:
        print(f"Node name: {deployment.node}")
        print(f"Deployed correctly: {deployment.prepared}")
        print(f"Error: {deployment.error}\n")

    # Start execution
    print("\nStarting experiment execution...")
    client.start_execution(experiment_name)

    # Wait for experiment to finish
    print("\nWaiting for experiment to finish...")
    while True:
        info = client.get_experiment_status(experiment_name)
        print(info.status)
        if info.status != ExperimentStatus.RUNNING:
            break
        time.sleep(10)

    # Print results
    print("\nExperiment results:")
    if info.execution_result:
        for report in info.execution_result:
            print(f"Node name: {report.node.name}")
            print(f"Error: {report.error}")

            result, log = report.result
            print(type(result))
            if isinstance(result, Result):
                data = result.unwrap() if is_successful(result) else result
                pprint(data)

            print("\nLogs:")
            for line in log:
                print(line.strip())
            print()
    else:
        print("No execution results available")

if __name__ == "__main__":
    main() 