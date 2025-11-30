---
slug: whats-new-thanksgiving-2025
title: "What's New in Baseboards: A Developer's Guide (With Minimal Sarcasm)"
authors:
  - cdiddy77
tags:
  - announcement
  - tutorial
  - nano-banana-pro
  - docker
  - architecture
  - developer-guide
description: A walkthrough of the latest Baseboards updates featuring Nano Banana Pro, the new create-baseboards CLI, and a deep dive into the Docker-based architecture that scales from local development to production.
---

Based on [the Loom walkthrough](https://www.loom.com/share/f496dcd5f36c49cb9d308667bff813dd)

## 1. Creating a New Baseboards Project

**[0:00](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=0)**

The walkthrough begins the way all good projects do: with a single command line incantation:

```bash
npx @weirdfingers/baseboards up my-boards-app
```

This command scaffolds a brand-new Baseboards project—frontend, backend, worker, and infrastructure templates included. If you’ve ever wished your “new project” button also came with working Docker orchestration and a GraphQL API, this is it.

---

## 2. API Keys & Docker: The “Why Is My Laptop Spinning Up Containers?” Section

**[0:11](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=11)**

You’ll enter a few model provider API keys, and then—almost before you can ask “is this strictly necessary?”—Docker Compose launches.

A reasonable question at this point:

> **Why Docker for a _local_ app? Isn’t Docker for, like, distributed systems and people who enjoy YAML?**

In Baseboards’ case, Docker gives us:

- isolated containers for Postgres, Redis, worker, and API services
- identical environments across local dev, staging, and production
- a deployment model that moves cleanly from “my laptop” → “my startup” → “my questionable future Kubernetes cluster”

Yes, it’s a lot of machinery for a local app.  
But it’s the same machinery you’ll want later when Baseboards is hosting thousands of artifacts instead of three test PNGs.

---

## 3. Scalability Isn’t Just Marketing

**[0:34](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=34)**

One of Baseboards’ goals is to scale to any deployment shape:

- **Kubernetes**: for the “I run a cluster and am emotionally prepared for this” crowd
- **Single backend**: the “just give me one machine that works” use case
- **Local development**: everything running neatly in containers, immune to dependency drift

The same architecture works across all three. That’s why we start on Docker—it’s the lowest common denominator that still behaves like a real distributed system.

---

## 4. Creating a New Board & Meeting Nano Banana Pro

**[1:09](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=69)**

Once the environment is up, you can head to `localhost:3300` and create a new board.  
Boards are the top-level containers for your artifacts—images, videos, text, audio, diagrams, all of it.

This release introduces support for:

### **Nano Banana Pro**

A shockingly good model for infographics, diagrams, and other structured image output.

---

## 5. Testing Nano Banana Pro With an Architectural Diagram

**[1:16](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=76)**

![Nano Banana Infographic Prompt](/img/blog/251130/prompt.png)

To test the model, we ask it to generate an architectural diagram of Baseboards itself.

The prompt was generated using Claude, which was asked to:

1. Look at the Baseboards project code
2. Summarize the system architecture
3. Produce a prompt describing that architecture visually

It’s AI analyzing code to produce a prompt for another AI to generate an image of the code used by the first AI.  
This is what software development looks like now. We’re all just living in it.

---

## 6. Monitoring the Worker and Logs

**[2:07](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=127)**

When the model is generating, you can:

- click into the job
- or—if you enjoy the feeling that you are in a late-90s hacker movie—  
  check the logs in the terminal.

(inside the project directory)

```bash
npx @eweirdfingers/baseboards logs -f
```

You’ll see the worker pick up the job, send it to Nano Banana Pro, receive the output, and push it back through the API.

![Logging Output](/img/blog/251130/logs.png)

Baseboards’ logs are human-readable, which is a refreshing change from certain systems we won’t name.

---

## 7. Infographic Success (Mostly)

**[2:37](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=157)**

When the worker finishes, the artifact appears directly on your board.

![Architecture Diagram](/img/blog/251130/arch-diagram.png)

The generated infographic:

- is visually clean
- maps the major components correctly
- contains several arrows
- and—most impressively—gets most of them pointing in the right direction

There are a few small hallucinations (e.g. Midjourney support, which Baseboards emphatically does _not_ have), but diagram-hallucination is a known side effect of models trying to be helpful.

---

## 8. Architecture Overview (AI-Generated, Human-Corrected)

**[3:07](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=187)**

The real Baseboards architecture looks like this:

- **Frontend (Next.js)**
- **FastAPI + GraphQL backend**
- **Postgres**
- **Redis**
- **Worker process**
- **Model provider**

The AI-generated diagram was close but forgot the part where the worker writes results _back_ to the database, which is arguably the most important arrow.  
We’ll blame the prompt, not the model.

---

## 9. Next Steps: Exploring the Project Structure

**[4:03](https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd?t=243)**

The next episode will dig into:

- what’s inside the generated Baseboards project
- how the API, worker, and frontend are wired together
- where to customize jobs and add new model providers
- how the Docker services communicate
- and how to extend Baseboards to support new artifact types

Think of this episode as the appetizer.  
Next time we go into the folder structure—the part everyone skips until something catches fire.

---

### **Full Video Walkthrough**

https://loom.com/share/f496dcd5f36c49cb9d308667bff813dd
