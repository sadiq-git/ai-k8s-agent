Diagnosis: AI saw ImagePullBackOff.

Action: It patched the deployment to nginx:latest.

Verification (The Looping): AI checked multiple times ("thrashing"). This is because Kubernetes is eventually consistent. The AI saw the old broken pod terminating and the new pod creating simultaneously. It kept checking until the new pod was fully Running.