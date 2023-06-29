from utils.constants import RUNPOD_API_KEY
import sys
import os
import runpod

# to create something more than this, we should be using the serverless endpoint when in production

llm_name = "tiiuae/falcon-7b-instruct" 
gpu_id = "NVIDIA A100 80GB PCIe"
quant = "bitsandbytes"

os.environ["RUNPOD_API_KEY"] = RUNPOD_API_KEY
runpod.api_key = os.getenv("RUNPOD_API_KEY", "0")


def write_runpod_id(runpod_id):
    with open("runpod_id.txt", "w") as file:
        file.write(runpod_id)

if(llm_name == "tiiuae/falcon-7b-instruct"):
    gpu_count = 1 # 1 for 7b and 40b quantization, 2 for 40b
    volume = 50 # 50 GB volume 
    disk_space = 10 # 10 GB disk space
    
    pod = runpod.create_pod(
        name="Cacti Falcon 7B",
        image_name="ghcr.io/huggingface/text-generation-inference:0.8.2",
        gpu_type_id= gpu_id,
        cloud_type= "SECURE",
        docker_args=f"--model-id {llm_name} --num-shard {gpu_count}",
        gpu_count=gpu_count,
        volume_in_gb=volume,
        container_disk_in_gb=disk_space,
        ports="80/http",
        volume_mount_path="/data", 
    ) # do not do quantization in small model.
    # os.environ['RUNPOD_ID'] = pod["id"]
    write_runpod_id(pod["id"])
    print("Starting runpod {pod_id} on model {llm_name}".format(pod_id=pod["id"], llm_name=llm_name))

elif(llm_name == "tiiuae/falcon-40b-instruct"):
    volume = 200 # 200 GB volume
    disk_space = 50 # 50 GB disk space
    
    if(quant == "bitsandbytes"):
        gpu_count = 1 # 1 for 7b and 40b quantization, 2 for 40b
        pod = runpod.create_pod(
            name="Cacti Falcon 40B quantized",
            image_name="ghcr.io/huggingface/text-generation-inference:0.8.2",
            gpu_type_id= gpu_id,
            cloud_type= "SECURE",
            docker_args=f"--model-id {llm_name} --num-shard {gpu_count}",
            gpu_count=gpu_count,
            volume_in_gb=volume,
            container_disk_in_gb=disk_space,
            ports="80/http",
            volume_mount_path="/data", 
        ) # do not do quantization in small model.
        write_runpod_id(pod["id"])
    
    else:
        gpu_count = 2
        pod = runpod.create_pod(
            name="Cacti Falcon 40B",
            image_name="ghcr.io/huggingface/text-generation-inference:0.8.2",
            gpu_type_id= gpu_id,
            cloud_type= "SECURE",
            docker_args=f"--model-id {llm_name} --num-shard {gpu_count}",
            gpu_count=gpu_count,
            volume_in_gb=volume,
            container_disk_in_gb=disk_space,
            ports="80/http",
            volume_mount_path="/data", 
        ) # do not do quantization in small model.
        write_runpod_id(pod["id"])
    
    print("Starting runpod {pod_id} on model {llm_name}".format(pod_id=pod["id"], llm_name=llm_name))
else:
    print("model name not supported, will not start a runpod container.")


