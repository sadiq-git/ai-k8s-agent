import os
import sys
import subprocess
import json
import platform
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

# --- Configuration ---
GROQ_MODEL = "llama-3.3-70b-versatile" 

# --- Helper for Windows Commands ---
def run_command(cmd_list):
    """
    Executes a command robustly on Windows and Linux.
    On Windows, we must use shell=True and pass a string, not a list.
    """
    try:
        if platform.system() == "Windows":
            # Windows fix: Join list into string and enable shell
            cmd_str = " ".join(cmd_list)
            result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        else:
            # Linux/Mac: Run as list is safer
            result = subprocess.run(cmd_list, capture_output=True, text=True)
            
        if result.returncode != 0:
            raise Exception(result.stderr.strip())
        return result.stdout.strip()
    except Exception as e:
        raise e

# --- Tools ---
@tool
def k8s_get_all_pods(namespace: str = "default") -> str:
    """Lists all pods in the namespace with status and specific failure reasons."""
    try:
        # Verify kubectl exists first
        try:
            run_command(["kubectl", "version", "--client"])
        except:
            return "CRITICAL ERROR: 'kubectl' command failed. Python cannot find it."

        # Get Pods
        json_out = run_command(["kubectl", "get", "pods", "-n", namespace, "-o", "json"])
        pods = json.loads(json_out)
        
        summary = []
        if not pods.get('items'): return "No pods found."
        
        for pod in pods['items']:
            name = pod['metadata']['name']
            status = pod['status']['phase']
            reasons = []
            
            # Check conditions for errors
            if 'status' in pod and 'containerStatuses' in pod['status']:
                for container in pod['status']['containerStatuses']:
                    state = container.get('state', {})
                    if 'waiting' in state: 
                        r = state['waiting'].get('reason')
                        m = state['waiting'].get('message', '')
                        reasons.append(f"Waiting ({r})")
            
            issue_str = f" | Issues: {'; '.join(reasons)}" if reasons else " | Healthy"
            summary.append(f"Pod: {name} | Status: {status}{issue_str}")
            
        return "\n".join(summary)
    except Exception as e: return f"Error execution: {str(e)}"

@tool
def k8s_describe_pod(pod_name: str, namespace: str = "default") -> str:
    """Describes a specific pod."""
    try:
        return run_command(["kubectl", "describe", "pod", pod_name, "-n", namespace])[:2000]
    except Exception as e: return f"Error: {e}"

@tool
def k8s_patch_image(deployment_name: str, new_image: str, namespace: str = "default") -> str:
    """Updates a deployment image."""
    try:
        print(f"\n⚡ EXECUTION: Patching {deployment_name} -> {new_image}")
        return run_command(["kubectl", "set", "image", f"deployment/{deployment_name}", f"*={new_image}", "-n", namespace])
    except Exception as e: return f"Error: {e}"

# --- Main Logic ---
def run_agent():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found.")
        return

    print(f"✅ Agent Initialized (Windows Compatibility Mode: {platform.system() == 'Windows'})")
    
    llm = ChatGroq(temperature=0, model_name=GROQ_MODEL, groq_api_key=api_key)
    tools = [k8s_get_all_pods, k8s_describe_pod, k8s_patch_image]
    tool_mapping = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=(
            "You are a Kubernetes SRE. "
            "1. ALWAYS run k8s_get_all_pods first to see the real names. "
            "2. Do NOT guess pod names. "
            "3. If you see ImagePullBackOff, find the deployment name and patch it to 'nginx:latest'."
        )),
        HumanMessage(content="Check default namespace for broken pods and fix them.")
    ]

    print("🚀 Starting SRE Loop...")
    
    while True:
        # A. Think
        print("🤖 AI is thinking...")
        try:
            ai_msg = llm_with_tools.invoke(messages)
        except Exception as e:
            print(f"❌ API Error: {e}")
            break

        messages.append(ai_msg)

        # B. Stop Condition
        if not ai_msg.tool_calls:
            print(f"\n✅ Mission Complete: {ai_msg.content}")
            break

        # C. Act
        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call["name"]
            args = tool_call["args"]
            print(f"🛠️  Tool: {tool_name} | Args: {args}")
            
            selected_tool = tool_mapping.get(tool_name)
            try:
                # Run the tool
                tool_output = selected_tool.invoke(args)
            except Exception as e:
                tool_output = f"Tool Failed: {e}"
            
            print(f"   -> Output: {str(tool_output)[:100]}...")
            messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))

if __name__ == "__main__":
    run_agent()