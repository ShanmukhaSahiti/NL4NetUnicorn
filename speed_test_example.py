#!/usr/bin/env python
# coding: utf-8

# # Basic Ookla Speed Test example
# 
# In this scenario, we will measure speed test results from Ookle speedtest-cli utility, capture PCAPs during measurements and upload them to a file storage for future access.
# 
# Let's import base classes and particular tasks that we will use:

# In[1]:


import os
import time

from netunicorn.client.remote import RemoteClient, RemoteClientException
from netunicorn.base import Experiment, ExperimentStatus, Pipeline

# Task using speedtest-cli to measure speedtest
from netunicorn.library.tasks.measurements.ookla_speedtest import OoklaSpeedtest

# Tasks to start tcpdump and stop named tcpdump task
from netunicorn.library.tasks.capture.tcpdump import StartCapture, StopNamedCapture

# Upload to file.io - public anonymous temporary file storage
from netunicorn.library.tasks.upload.fileio import UploadToFileIO


# Now, let's create a pipeline. We would like to start the tcpdump (network traffic capturing), then do speedtest several times, then stop capturing the data and upload it to some temporary file storage (we chose `https://file.io` website for this, and no, they haven't paid us for the advertisement).

# In[2]:


pipeline = (
    Pipeline()
    .then(StartCapture(filepath="/tmp/capture.pcap", name="capture"))
)

for _ in range(3):
    pipeline.then(OoklaSpeedtest())

pipeline = (
    pipeline
    .then(StopNamedCapture(start_capture_task_name="capture"))
    .then(UploadToFileIO(filepath="/tmp/capture.pcap", expires="1d"))
)


# After we decided what our pipeline would look like, we need to connect to some netunicorn instance and get nodes we will run our pipeline on. If you have `.env` file with credential in the folder, we need to read it, and then try to read needed parameters from environment variables.
# 
# If no `.env` file or parameters in environment variables are provided, let's assume you're working with local installation of netunicorn with the default endpoint address and credentials. If this is not the case, feel free to modify the next variables.

# In[3]:


# if you have .env file locally for storing credentials, skip otherwise
if '.env' in os.listdir():
    from dotenv import load_dotenv
    load_dotenv(".env")


# In[4]:


NETUNICORN_ENDPOINT = os.environ.get('NETUNICORN_ENDPOINT', 'https://pinot.cs.ucsb.edu/netunicorn')
NETUNICORN_LOGIN = os.environ.get('NETUNICORN_LOGIN', '293nmay25')
NETUNICORN_PASSWORD = os.environ.get('NETUNICORN_PASSWORD', '4Ij9Du65jrqj')


# Connect to the instance and verify that it's healthy.

# In[5]:


client = RemoteClient(endpoint=NETUNICORN_ENDPOINT, login=NETUNICORN_LOGIN, password=NETUNICORN_PASSWORD)
client.healthcheck()


# Great!
# 
# Now, let's ask for some nodes. For demonstration purposes we will take some nodes from our infrastructures that have names like `raspi-blablabla` (look at the filter function below). If you have local installation, let's take a single node. If you use your own infrastructure, feel free to modify the example.

# In[6]:


nodes = client.get_nodes()
print("All available nodes:")
print(nodes)


# In[7]:


# switch for showing our infrastructure vs you doing it locally on other nodes
if os.environ.get('NETUNICORN_ENDPOINT', 'https://pinot.cs.ucsb.edu/netunicorn') != 'http://localhost:26611':
    working_nodes = nodes.filter(lambda node: node.name == "snl-server-5").take(1)
else:
    working_nodes = nodes.take(1)

print("\nSelected working nodes:")
print(working_nodes)


# Afterwards, we need to create the experiment -- let's assign the same pipeline to all nodes!

# In[8]:


experiment = Experiment().map(pipeline, working_nodes)


# In[9]:


experiment


# Now, we defined the pipeline and the experiment, so it's time to prepare it...

# In[10]:


experiment_label = "speed_test_example"
try:
    client.delete_experiment(experiment_label)
except RemoteClientException:
    pass

client.prepare_experiment(experiment, experiment_label)


# ...and wait while it's compiling and distributing to nodes.

# In[11]:


while True:
    info = client.get_experiment_status(experiment_label)
    print(info.status)
    if info.status == ExperimentStatus.READY:
        break
    time.sleep(20)


# As soon as the experiment is READY, let's start it.

# In[12]:


client.start_execution(experiment_label)


# In[13]:


while True:
    info = client.get_experiment_status(experiment_label)
    print(info.status)
    if info.status != ExperimentStatus.RUNNING:
        break
    time.sleep(20)


# If (we hope in your case too) the experiment is finished, we can explore the resulting object with execution information, such as errors, results of execution, and raw logs of all tasks in each deployment. 

# In[14]:


from returns.pipeline import is_successful
from returns.result import Result

for report in info.execution_result:
    print(f"Node name: {report.node.name}")
    print(f"Error: {report.error}")

    result, log = report.result  # report stores results of execution and corresponding log
    
    # result is a returns.result.Result object, could be Success of Failure
    print(f"Result is: {type(result)}")
    if isinstance(result, Result):
        data = result.unwrap() if is_successful(result) else result
        for key, value in data.items():
            print(f"{key}: {value}")

    # we also can explore logs
    for line in log:
        print(line.strip())
    print()


# As you see, in this example we successfully measured speed test several times from our nodes, captured the traffic and uploaded the data to the cloud. Now the only thing left is to explore it and draw some conclusions, but we will leave this to you. :)
# 
# Please, visit the https://netunicorn.cs.ucsb.edu website if you look for additional documentation or information regarding this platform, usage, and API.
