import yaml
import argparse

def main():
    parser = argparse.ArgumentParser(description="TCPX Job Manifest Generator")
    parser.add_argument("-f", "--file", required=True, help="Path to your job template YAML file")
    parser.add_argument("-n", "--nccl", required=True, help="NCCL plugin version")
    parser.add_argument("-r", "--rxdm", required=True, help="RxDM version")
    # parser.add_argument("-y", "--yes", action="store_true", help="Auto-consent to continue even if version combination is not listed (use with caution)")

    args = parser.parse_args()

    # Step 1: Get the YAML file from the user
    if not args.file:
        args.file = input("Please provide the path to your job template YAML file: ")
        
    # Step 2: Open the compatibility list link
    # compatibility_link = "https://docs.google.com/document/d/1D5umT4-WDuNnYf3ieQ5SfLdmvGRPBQGLB662udzwz8I"  # Replace with the actual link
    # print(f"Please check this link for supported version combinations for NCCL plugin and RxDM: {compatibility_link}")

    # Step 3: Get user consent
    # if not args.yes:  # Don't ask for consent if -y is provided
    #     compatibility_link = "https://docs.google.com/document/d/1D5umT4-WDuNnYf3ieQ5SfLdmvGRPBQGLB662udzwz8I"
    #     print(f"Please check this link for supported version combinations for NCCL plugin and RxDM: {compatibility_link}")
    #     consent = input("Version combination not listed in the link might impact performance, please consent to continue (yes/no): ")
    #     if consent.lower() != "yes" and consent.lower() != "y":
    #         print("Exiting the script. Please choose supported versions.")
    #         return

    # Step 4: Get component versions from user
    if not args.nccl:
        args.nccl = input("Enter the NCCL plugin version: ")
    if not args.rxdm:
        args.rxdm = input("Enter the RxDM version: ")

    # Step 5: Load and modify the YAML
    with open(args.file, "r") as file:
        job_manifest = yaml.safe_load(file)

    # Update annotations
    add_annotations(job_manifest)

    # # Update volumes
    add_volumes(job_manifest)

    # # Add tcpx-daemon container
    add_tcpx_daemon_container(job_manifest, args.rxdm)

    # # Update environment variables and volumeMounts for GPU containers
    update_gpu_containers(job_manifest)

    # Step 6: Generate the new YAML file
    updated_job = str(yaml.safe_dump(job_manifest, default_flow_style=False, width=1000, default_style="|", sort_keys=False)).replace("|-", "")

    new_file_name = args.file.replace(".yaml", "-tcpx.yaml")
    with open(new_file_name, "w", encoding="utf-8") as file:
        file.write(updated_job)

    # Step 7: Provide instructions to the user
    print("\nPlease follow the below steps to complete enabling TCPX:")
    print("1. Deploy NCCL plugin component if it haven't been deploy (update version):")
    print("   kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/gpudirect-tcpx/nccl-tcpx-installer.yaml")
    print("   (Replace 'nccl-tcpx-installer.yaml' with the correct version)")
    print("2. Deploy NRI device injector plugin if it haven't been deploy :")
    print("   kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nri_device_injector/nri-device-injector.yaml")
    print("3. Deploy your workload with the updated manifest:", new_file_name)
    print("4. Verify your workload is working as expected")

def add_annotations(job_manifest):
    annotations = {
        'devices.gke.io/container.tcpx-daemon':"""|+
- path: /dev/nvidia0
- path: /dev/nvidia1
- path: /dev/nvidia2
- path: /dev/nvidia3
- path: /dev/nvidia4
- path: /dev/nvidia5
- path: /dev/nvidia6
- path: /dev/nvidia7
- path: /dev/nvidiactl
- path: /dev/nvidia-uvm""",
        "networking.gke.io/default-interface": "eth0",
        "networking.gke.io/interfaces":"""|
[
    {"interfaceName":"eth0","network":"default"},
    {"interfaceName":"eth1","network":"vpc0"},
    {"interfaceName":"eth2","network":"vpc1"},
    {"interfaceName":"eth3","network":"vpc2"},
    {"interfaceName":"eth4","network":"vpc3"}
]""",
    }

    # Create path if it doesn't exist
    job_manifest.setdefault("spec", {}).setdefault("template", {}).setdefault("metadata", {})

    # Add/update annotations
    pod_template_spec = job_manifest["spec"]["template"]["metadata"]
    if "annotations" in pod_template_spec:
        pod_template_spec["annotations"].update(annotations)
    else:
        pod_template_spec["annotations"] = annotations

def add_volumes(job_manifest):
    volumes = [
        {"name": "libraries", "hostPath": {"path": "/home/kubernetes/bin/nvidia/lib64"}},
        {"name": "tcpx-socket", "emptyDir": {}},
        {"name": "sys", "hostPath": {"path": "/sys"}},
        {"name": "proc-sys", "hostPath": {"path": "/proc/sys"}},
    ]

    # Create path if it doesn't exist
    job_manifest.setdefault("spec", {}).setdefault("template", {}).setdefault("spec", {})

    # Add volumes
    pod_spec = job_manifest["spec"]["template"]["spec"]
    if "volumes" in pod_spec:
        pod_spec["volumes"].extend(volumes)
    else:
        pod_spec["volumes"] = volumes


def add_tcpx_daemon_container(job_template, rxdm_version):
    tcpx_daemon_container = {
        "name": "tcpx-daemon",
        "image": f"us-docker.pkg.dev/gce-ai-infra/gpudirect-tcpx/tcpgpudmarxd-dev:{rxdm_version}",   # Use provided RxDM version
        "imagePullPolicy": "Always",
        "command": 
        """- /tcpgpudmarxd/build/app/tcpgpudmarxd
- --gpu_nic_preset
- a3vm
- --gpu_shmem_type
- fd
- --uds_path
- /run/tcpx
- --setup_param
- \\\"--verbose 128 2 0 \\\"""",
        "securityContext": {
            "capabilities": {"add": ["NET_ADMIN"]}
        },
        "volumeMounts": [
            {"name": "libraries", "mountPath": "/usr/local/nvidia/lib64"},
            {"name": "tcpx-socket", "mountPath": "/run/tcpx"},
            {"name": "sys", "mountPath": "/hostsysfs"},
            {"name": "proc-sys", "mountPath": "/hostprocsysfs"},
        ],
        "env": [{"name": "LD_LIBRARY_PATH", "value": "/usr/local/nvidia/lib64"}],
    }

    # Create path if it doesn't exist
    job_template.setdefault("spec", {}).setdefault("template", {}).setdefault("spec", {})

    # Add container
    pod_spec = job_template["spec"]["template"]["spec"]
    pod_spec.setdefault("containers", []).insert(0, tcpx_daemon_container)

def update_gpu_containers(job_manifest):
    env_vars = [{"name": "LD_LIBRARY_PATH", "value": "/usr/local/nvidia/lib64"}]
    volume_mounts = [
        {"name": "tcpx-socket", "mountPath": "/tmp"},
        {"name": "libraries", "mountPath": "/usr/local/nvidia/lib64"},
    ]

    pod_spec = job_manifest.get("spec", {}).get("template", {}).get("spec", {})
    for container in pod_spec.get("containers", []):
        # Create path if it doesn't exist
        container.setdefault("env", [])
        container.setdefault("volumeMounts", [])
        if container.get("resources", {}).get("limits", {}).get("nvidia.com/gpu", 0) > 0:
            container["env"].extend(env_vars)
            container["volumeMounts"].extend(volume_mounts)

if __name__ == "__main__":
    main()

