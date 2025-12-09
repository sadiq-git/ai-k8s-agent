import os
import subprocess
import json
import platform
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

# --- Configuration ---
GROQ_MODEL = "llama-3.3-70b-versatile" 

# --- Helper: Robust Command Execution ---
def run_command(cmd_list):
    try:
        if platform.system() == "Windows":
            cmd_str = " ".join(cmd_list)
            # Merge stderr into stdout to capture all output
            result = subprocess.run(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
        else:
            result = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# --- Tool 1: K8s Inspector ---
@tool
def k8s_get_all_pods(namespace: str = "default") -> str:
    """Lists all pods with status and image versions."""
    output = run_command(["kubectl", "get", "pods", "-n", namespace, "-o", "json"])
    try:
        # Extract JSON if mixed with logs
        start = output.find('{')
        if start == -1: return "Error: No JSON found in kubectl output."
        pods = json.loads(output[start:])
    except Exception as e:
        return f"Error parsing kubectl: {e}"
        
    summary = []
    if not pods.get('items'): return "No pods found."
    
    for pod in pods['items']:
        name = pod['metadata']['name']
        status = pod['status']['phase']
        # Safe access to image field
        try:
            image = pod['spec']['containers'][0]['image']
        except:
            image = "unknown"
        summary.append(f"Pod: {name} | Status: {status} | Image: {image}")
        
    return "\n".join(summary)

# --- Tool 2: K8s Patcher ---
@tool
def k8s_patch_image(deployment_name: str, new_image: str, namespace: str = "default") -> str:
    """Updates a deployment to a secure image version."""
    print(f"\n⚡ ACTION: Patching '{deployment_name}' -> '{new_image}'")
    return run_command(["kubectl", "set", "image", f"deployment/{deployment_name}", f"*={new_image}", "-n", namespace])

# --- Tool 3: Security Scanner (Fixed) ---
@tool
def security_scan_image(image_name: str) -> str:
    """
    Scans a container image for CRITICAL vulnerabilities.
    """
    print(f"\n🛡️  SECURITY: Scanning '{image_name}' (this may take 10-20s)...")
    
    # Added --quiet to reduce Docker noise
    cmd = [
        "docker", "run", "--rm", 
        "aquasec/trivy", "image", 
        "--severity", "CRITICAL", 
        "--format", "json", 
        "--scanners", "vuln",
        "--quiet",
        image_name
    ]
    
    raw_output = run_command(cmd)
    
    try:
        # ROBUST PARSING: Find the *last* valid JSON object if multiple exist
        # or simply find the first '{' and last '}'
        start_idx = raw_output.find('{')
        end_idx = raw_output.rfind('}') + 1
        
        if start_idx == -1: 
            return f"Scan failed. Output: {raw_output[:200]}"
            
        json_str = raw_output[start_idx:end_idx]
        report = json.loads(json_str)
        
        cve_list = []
        if 'Results' in report:
            for res in report['Results']:
                for vuln in res.get('Vulnerabilities', []):
                    cve_list.append(f"{vuln['VulnerabilityID']} ({vuln['PkgName']})")
        
        count = len(cve_list)
        if count > 0:
            return f"❌ VULNERABLE: Found {count} CRITICAL issues: {', '.join(cve_list[:3])}..."
        return "✅ SECURE: No critical vulnerabilities."

    except Exception as e:
        return f"Error reading scan report: {e}"

# --- Main Agent Loop ---
def run_agent():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key: return

    llm = ChatGroq(temperature=0, model_name=GROQ_MODEL, groq_api_key=api_key)
    tools = [k8s_get_all_pods, k8s_patch_image, security_scan_image]
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    print(f"✅ DevSecOps Agent Online (Model: {GROQ_MODEL})")
    print("   Monitoring Cluster for Security Compliance...")

    messages = [
        SystemMessage(content=(
            "You are a DevSecOps Guard. "
            "1. Audit all pods. "
            "2. If you see 'alpine:3.10', it is BANNED. Scan it to confirm why, then PATCH it to 'alpine:3.20' immediately. "
            "3. If you see 'nginx', just scan it and report status. "
            "4. Be concise."
        )),
        HumanMessage(content="Perform security audit now.")
    ]
    
    while True:
        print("🤖 ...")
        ai_msg = llm_with_tools.invoke(messages)
        messages.append(ai_msg)

        if not ai_msg.tool_calls:
            print(f"\n📝 FINAL REPORT: {ai_msg.content}")
            break

        for tool_call in ai_msg.tool_calls:
            print(f"🛠️  {tool_call['name']} args={tool_call['args']}")
            tool_output = tool_map[tool_call['name']].invoke(tool_call['args'])
            print(f"   -> {str(tool_output)[:100]}...")
            messages.append(ToolMessage(tool_call_id=tool_call['id'], content=str(tool_output)))

if __name__ == "__main__":
    run_agent()