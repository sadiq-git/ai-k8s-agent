import os
import subprocess
import json
import platform
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

# --- Configuration ---
GROQ_MODEL = "llama-3.3-70b-versatile" 

# --- Helper for Windows/Docker Commands ---
def run_command(cmd_list):
    try:
        if platform.system() == "Windows":
            # Windows shell fix
            cmd_str = " ".join(cmd_list)
            result = subprocess.run(cmd_str, capture_output=True, text=True, shell=True)
        else:
            result = subprocess.run(cmd_list, capture_output=True, text=True)
            
        return result.stdout.strip() + result.stderr.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# --- Existing K8s Tools ---
@tool
def k8s_get_all_pods(namespace: str = "default") -> str:
    """Lists all pods with status."""
    json_out = run_command(["kubectl", "get", "pods", "-n", namespace, "-o", "json"])
    try:
        pods = json.loads(json_out)
    except:
        return "Error parsing kubectl output. Is the cluster reachable?"
        
    summary = []
    if not pods.get('items'): return "No pods found."
    
    for pod in pods['items']:
        name = pod['metadata']['name']
        status = pod['status']['phase']
        image = pod['spec']['containers'][0]['image']
        summary.append(f"Pod: {name} | Status: {status} | Image: {image}")
        
    return "\n".join(summary)

@tool
def k8s_patch_image(deployment_name: str, new_image: str, namespace: str = "default") -> str:
    """Updates a deployment image."""
    print(f"\n⚡ EXECUTION: Patching {deployment_name} -> {new_image}")
    return run_command(["kubectl", "set", "image", f"deployment/{deployment_name}", f"*={new_image}", "-n", namespace])

# --- NEW: Security Tool ---
@tool
def security_scan_image(image_name: str) -> str:
    """
    Scans a container image for CRITICAL vulnerabilities using Docker+Trivy.
    Returns a summary of High/Critical issues.
    """
    print(f"\n🛡️  SECURITY: Scanning image '{image_name}' for vulnerabilities...")
    
    # We run Trivy via Docker so you don't need to install it manually
    cmd = [
        "docker", "run", "--rm", 
        "aquasec/trivy", "image", 
        "--severity", "CRITICAL", 
        "--format", "json", 
        "--scanners", "vuln", # fast mode
        image_name
    ]
    
    output = run_command(cmd)
    
    try:
        # Find the JSON start (ignore docker pull logs)
        json_start = output.find('{')
        if json_start == -1: return "Scan Failed: No JSON output."
        
        report = json.loads(output[json_start:])
        
        cve_count = 0
        details = []
        
        if 'Results' in report:
            for result in report['Results']:
                if 'Vulnerabilities' in result:
                    for vuln in result['Vulnerabilities']:
                        cve_count += 1
                        details.append(f"{vuln['VulnerabilityID']} ({vuln['PkgName']})")
        
        if cve_count > 0:
            return f"⚠️ UNSECURE: Found {cve_count} CRITICAL vulnerabilities: {', '.join(details[:5])}..."
        else:
            return "✅ SECURE: No Critical vulnerabilities found."
            
    except Exception as e:
        return f"Error parsing scan results: {e}. Raw Output: {output[:200]}"

# --- Main Logic ---
def run_agent():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return

    llm = ChatGroq(temperature=0, model_name=GROQ_MODEL, groq_api_key=api_key)
    
    # We add the security tool to the kit
    tools = [k8s_get_all_pods, k8s_patch_image, security_scan_image]
    tool_mapping = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    print(f"✅ DevSecOps Agent Initialized with {len(tools)} tools.")

    messages = [
        SystemMessage(content=(
            "You are a DevSecOps AI. "
            "1. List pods to see what images are running. "
            "2. If an image is 'nginx:latest' or 'alpine:3.10', SCAN it using security_scan_image. "
            "3. If 'alpine:3.10' has critical vulnerabilities, PATCH it to 'alpine:3.20'. "
            "4. Report your findings."
        )),
        HumanMessage(content="Audit the running pods for security issues.")
    ]
    
    while True:
        print("🤖 AI is thinking...")
        ai_msg = llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            print(f"\n✅ Mission Complete: {ai_msg.content}")
            break

        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call["name"]
            args = tool_call["args"]
            print(f"🛠️  Tool: {tool_name} | Args: {args}")
            
            tool_output = tool_mapping[tool_name].invoke(args)
            
            # Print short preview of output
            print(f"   -> Output: {str(tool_output)[:150]}...")
            messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(tool_output)))

if __name__ == "__main__":
    run_agent()