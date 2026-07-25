# DevOps Hands-On Session — MCA Sem 1 & Sem 3

End-to-end demo repo and runbook for a 4-topic hands-on DevOps session:
**DevOps Introduction → GitHub Actions → Jenkins (Install & Plugins) → Kubernetes Basics.**

The whole session is built around **one tiny sample app** carried through all 4 topics, so students see
the *same* change flow automated by three different tools. That continuity is the main teaching device —
call it out explicitly at the start of the session.

- **Sem 1 audience**: zero DevOps exposure. Lean on the "why" — pain of doing things manually, then the
  relief of automation. Don't over-explain YAML syntax; focus on cause → effect (I pushed code → this
  happened).
- **Sem 3 audience**: already introduced to DevOps concepts. Go one level deeper into mechanics — YAML
  structure, plugin architecture, kubectl verbs — and connect each tool to where it sits in the DevOps
  lifecycle.

---

## Repo contents

| File | Purpose |
|---|---|
| `app.py` | Tiny Flask app — `/` returns a greeting, `/health` returns JSON status |
| `requirements.txt` | `flask`, `pytest` |
| `test_app.py` | 2 pytest tests against the Flask app |
| `Dockerfile` | Builds the app into a container image |
| `.github/workflows/ci.yml` | GitHub Actions CI workflow |
| `Jenkinsfile` | Jenkins Pipeline definition (mirrors the GH Actions workflow) |
| `k8s/deployment.yaml` | Kubernetes Deployment (2 replicas) |
| `k8s/service.yaml` | Kubernetes NodePort Service |

---

## Prerequisites (verify on the actual delivery machine beforehand)

- Docker installed and working — test with `docker run hello-world` **and** a port-mapped container
  (`docker run -d -p 8888:80 nginx` then `curl localhost:8888`) to catch networking issues ahead of time.
- Python 3.10+ and `pip`
- Git + a GitHub account
- `kubectl` CLI
- `kind` CLI (Kubernetes-in-Docker) — single binary, no sudo needed:
  ```bash
  curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.29.0/kind-linux-amd64
  chmod +x ./kind
  mv ./kind ~/.local/bin/kind
  ```
- `gh` (GitHub CLI) — optional, makes pushing/creating repos faster live

**Known gotcha to test ahead of time:** on some machines/sandboxes, Docker's iptables NAT chains
(`DOCKER`, `DOCKER-FORWARD`) can go missing, which breaks port-mapped containers *and* `kind` cluster
creation (`kind` needs to create its own bridge network). If you hit
`iptables: No chain/target/match by that name` from Docker, the fix is:
```bash
sudo systemctl restart docker
```
This was needed once during our own rehearsal and fixed it immediately. Rehearse `kind create cluster`
end-to-end on the actual lab machine before the session — don't discover this live.

---

## Topic 1 — DevOps Introduction (concept + manual-pain demo)

**Goal:** before automating anything, make students *feel* the manual cycle — that's the motivation for
everything that follows.

**Concept (15 min):** Dev vs Ops silos → what breaks when they don't talk (slow releases, "works on my
machine", manual deploy mistakes) → the DevOps lifecycle (Plan → Code → Build → Test → Release → Deploy →
Operate → Monitor) → where GitHub Actions / Jenkins / Kubernetes each sit in that lifecycle.

**Hands-on — do the full cycle by hand and count the steps:**

```bash
git clone <repo-url>
cd devops-session

# 1. set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. run tests manually
pytest -q
# → 2 passed

# 3. run the app manually
python app.py &
curl localhost:5000/
curl localhost:5000/health
kill %1

# 4. build a container image manually
docker build -t devops-session-app:manual .

# 5. run the container manually
docker run -d --rm -p 5001:5000 --name devops-manual-demo devops-session-app:manual
curl localhost:5001/
curl localhost:5001/health
docker stop devops-manual-demo
```

**Debrief for students:** "That's 5 manual steps, every single time you change one line of code. Now
imagine doing that 10 times a day, across a team of 20 engineers, without ever forgetting a step or fat
fingering a command. That pain is exactly what CI/CD tools remove." → segues straight into GitHub Actions.

---

## Topic 2 — GitHub Actions

**Concept (10–15 min):** What is CI/CD. YAML workflow anatomy — `on:` (triggers), `jobs:`, `steps:`,
runners. Where the workflow file lives (`.github/workflows/`).

**Hands-on — write and push a CI workflow:**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
    paths:
      - "app.py"
      - "test_app.py"
      - "requirements.txt"
      - "Dockerfile"
      - ".github/workflows/ci.yml"
  pull_request:
    branches: [main]
    paths:
      - "app.py"
      - "test_app.py"
      - "requirements.txt"
      - "Dockerfile"
      - ".github/workflows/ci.yml"
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest -q

      - name: Build Docker image
        run: docker build -t devops-session-app:${{ github.sha }} .
```

```bash
git add .github/workflows/ci.yml
git commit -m "Add GitHub Actions CI workflow"
git push
```

Watch it run live: GitHub repo → **Actions** tab, or via CLI:
```bash
gh run list --repo <owner>/<repo>
gh run watch <run-id> --repo <owner>/<repo> --exit-status
```

### Live demo: break it, watch it fail, fix it

```bash
# in test_app.py, add a deliberately failing assertion:
#     assert 1 == 2  # intentional break for the live demo
git add -A && git commit -m "Break test intentionally for live demo" && git push
```
→ Actions tab shows a **red ✗**. Open the run, show students the failing pytest output in the logs.

```bash
# remove the bad assertion
git add -A && git commit -m "Fix broken test" && git push
```
→ Actions tab shows **green ✓** again. This fail → read logs → fix → pass loop *is* the core CI habit
you're teaching.

### Controlling *when* CI runs (important lesson — don't let CI run on every trivial change)

Two levers, both already in `ci.yml` above:

1. **`paths:` filter** — only triggers the workflow when files that actually matter changed. Prove it:
   ```bash
   echo "unrelated notes" > NOTES.md
   git add -A && git commit -m "Add unrelated notes file" && git push
   gh run list --repo <owner>/<repo> --limit 3
   # → no new run appears for this commit
   ```
2. **`workflow_dispatch:`** — adds a manual **"Run workflow"** button in the Actions tab, and enables:
   ```bash
   gh workflow run CI --repo <owner>/<repo>
   ```
   Good for demonstrating on-demand runs (e.g. before a release) independent of any push.

**Teaching point:** real teams almost always scope CI triggers — path filters to avoid wasted runs on
docs-only changes, `workflow_dispatch` for on-demand runs, and (mention, don't need to demo)
`[skip ci]` in a commit message as another common escape hatch.

---

## Topic 3 — Jenkins (Installation & Plugins)

**Concept (10 min):** Jenkins vs GitHub Actions — same CI concept, self-hosted vs SaaS. Controller/agent
model. Freestyle jobs vs Pipeline-as-code (`Jenkinsfile`). Jenkins' plugin-driven architecture (7000+
plugins vs GitHub's marketplace-of-actions model).

### Step 1 — Install Jenkins via Docker

```bash
docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts
```
> Note: if port 8080 is taken on the demo machine, either stop whatever's using it or add
> `--httpPort=8081` at the end of the command and change `-p 8081:8081` accordingly.
> Mounting the Docker socket lets Jenkins later run `docker build` steps directly — needed for the
> pipeline in Step 4.

Wait ~1–2 minutes for first boot (mention this explicitly — nothing happens visibly for a while, don't
panic), then get the initial admin password:
```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### Step 2 — Unlock Jenkins (browser)

1. Open `http://localhost:8080` (or `:8081` if you changed the port)
2. Paste the initial admin password
3. Choose **"Install suggested plugins"** (or "Select plugins to install" if you want more control)
4. Create your first admin user when prompted

### Step 3 — Install plugins manually (the core hands-on for this topic)

**Manage Jenkins → Plugins → Available plugins**, search and select each, then click **Install**:

| Plugin | What it does | Why we need it here |
|---|---|---|
| **Git** | Lets Jenkins clone/checkout a Git repository as a build step | Without it Jenkins can't pull source code from GitHub at all |
| **Pipeline** (`workflow-aggregator`) | Enables Pipeline-as-code — defining the build in a `Jenkinsfile` checked into the repo | The modern way to define CI/CD in Jenkins, instead of clicking through a Freestyle job's UI |
| **Docker Pipeline** (`docker-workflow`) | Lets a Jenkinsfile run `docker build` / `docker run` steps | Our sample app ships a Dockerfile; we want Jenkins to build it, mirroring GitHub Actions |

Check the **"Restart Jenkins when installation is complete"** box. **Heads-up:** in a Dockerized Jenkins,
this restart stops the Jenkins *process*, and since there's no restart policy on the container by default,
the container itself can exit. If the browser tab goes blank and stays unreachable:
```bash
docker start jenkins
```
This is genuinely worth mentioning to students proactively — better than looking like something broke.

### Step 4 — Create a Pipeline job

`Jenkinsfile` (already in this repo):
```groovy
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install & Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r requirements.txt
                    pytest -q
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t devops-session-app:jenkins-${BUILD_NUMBER} .'
            }
        }
    }
}
```

In Jenkins UI:
1. **New Item** → name it `devops-session-pipeline` → type **Pipeline** → OK
2. Under **Pipeline** section: Definition = **Pipeline script from SCM**, SCM = **Git**,
   Repository URL = this repo's GitHub URL, Branch = `*/main`, Script Path = `Jenkinsfile`
3. **Save**, then click **Build Now**
4. Open the build → **Console Output** to show students the live log — checkout, pytest run, docker build,
   `Finished: SUCCESS`

**Prerequisite the Jenkins container needs for stage 3 to work:** Python and the Docker CLI must be
available *inside* the Jenkins container, and the container's `jenkins` user needs access to the mounted
Docker socket:
```bash
# one-time setup inside the running container
docker exec -u 0 jenkins bash -c "
  groupadd -g <host-docker-gid> dockerhost 2>/dev/null || true
  usermod -aG dockerhost jenkins
  apt-get update -qq && apt-get install -y -qq python3 python3-venv python3-pip docker.io
"
docker restart jenkins   # group membership only applies after a restart
```
Find `<host-docker-gid>` via `getent group docker` on the host. **This is fiddly enough that for a first
Jenkins session, consider dropping the "Build Docker Image" stage entirely** and just doing Checkout +
Test — that alone teaches the core Pipeline concept without debugging socket permissions live in front of
60 students. Pre-baking a custom Jenkins image with this already configured is the better option if you
want to keep the Docker stage.

---

## Topic 4 — Kubernetes Basics

**Concept (15 min):** Why orchestration (one Docker container isn't enough — need scaling, self-healing,
rolling updates). Core objects in plain words:
- **Pod** — smallest deployable unit, one or more containers that live/die together
- **Deployment** — keeps N replicas of a Pod running, replaces dead ones automatically
- **Service** — stable network identity + load balancing across a Deployment's Pods (Pods' IPs change
  constantly; Services don't)

### Step 1 — Create a local cluster

```bash
kind create cluster --name devops-session
kubectl cluster-info --context kind-devops-session
kubectl get nodes -o wide
```

### Step 2 — Load the app image into the cluster

`kind` clusters can't pull from the internet by default for a locally-built image — load it directly:
```bash
docker build -t devops-session-app:manual .
kind load docker-image devops-session-app:manual --name devops-session
```

### Step 3 — Deploy it

`k8s/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devops-session-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devops-session-app
  template:
    metadata:
      labels:
        app: devops-session-app
    spec:
      containers:
        - name: devops-session-app
          image: devops-session-app:manual
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 5000
```

`k8s/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: devops-session-app
spec:
  type: NodePort
  selector:
    app: devops-session-app
  ports:
    - port: 80
      targetPort: 5000
      nodePort: 30080
```

```bash
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
kubectl get deployments,pods,svc -o wide
```

### Step 4 — Access the app

`kind` node containers don't expose NodePort to the host by default, so use `kubectl port-forward` —
also a genuinely useful real-world debugging technique to teach:
```bash
kubectl port-forward svc/devops-session-app 8090:80
```
Then in another terminal / browser:
```
http://localhost:8090/
http://localhost:8090/health
```

### Step 5 — Self-healing demo

```bash
kubectl get pods -l app=devops-session-app
POD=$(kubectl get pods -l app=devops-session-app -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"          # simulate a crash
kubectl get pods -l app=devops-session-app
# → a brand-new pod appears automatically, replacing the deleted one; replica count stays at 2
```

### Step 6 — Scaling demo

```bash
kubectl scale deployment devops-session-app --replicas=4
kubectl get pods -l app=devops-session-app
# → 4 pods running

kubectl scale deployment devops-session-app --replicas=2
kubectl get pods -l app=devops-session-app
# → scales back down to 2
```

### Bonus Q&A talking points (came up in rehearsal — good to pre-empt)

**"Does `kubectl port-forward` work the same way in production (e.g. AKS)?"**
Yes, mechanically identical — but it's a debugging tool, not how real traffic reaches the app.
Flow: your machine → Kubernetes API server (authenticated) → kubelet on the node → **one specific pod**.
It bypasses the Service's load-balancing entirely. Real production traffic instead goes through:
- **Service `type: LoadBalancer`** — provisions a real cloud load balancer with a public/internal IP
- **Ingress Controller** (NGINX Ingress, or AGIC on Azure) — one entry point, host/path routing, TLS
- **Azure Application Gateway / Front Door** — often sits in front of Ingress for WAF + global routing

**"Does using port-forward on a production service impact end users?"**
No — it never touches the Service's `iptables`/IPVS routing rules, so it can't affect how real traffic is
load-balanced. It pins to one backing pod for the session (not round-robined like real Service traffic),
and the only real effect is that your own debug requests count as load on that one pod, same as any other
client. Just don't load-test through a port-forward against a production pod — it's not representative
(single pod, no LB) and adds real load to something serving real users.

---

## Cleanup (after the session)

```bash
# Kubernetes
kubectl delete -f k8s/deployment.yaml -f k8s/service.yaml
kind delete cluster --name devops-session

# Jenkins
docker stop jenkins && docker rm jenkins
docker volume rm jenkins_home   # only if you don't want to keep Jenkins config/history

# local containers/images
docker rm -f devops-manual-demo 2>/dev/null
docker rmi devops-session-app:manual devops-session-app:jenkins-1 2>/dev/null

# python venv
deactivate 2>/dev/null
rm -rf .venv
```

---

## Timing guide (per topic, ~60–75 min total)

| Topic | Concept | Hands-on | Buffer |
|---|---|---|---|
| DevOps Intro | 15 min | 15 min | 5 min |
| GitHub Actions | 10 min | 25 min | 10 min |
| Jenkins | 10 min | 30 min | 10 min |
| Kubernetes | 15 min | 25 min | 10 min |

Labs always have someone stuck on PATH issues, Docker permissions, or a typo — the buffer isn't optional.
