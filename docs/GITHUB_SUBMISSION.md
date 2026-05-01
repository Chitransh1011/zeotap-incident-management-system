# GitHub and PDF Submission Guide

## 1. Create GitHub Repository

Create a new public or private GitHub repository, for example:

```text
zeotap-incident-management-system
```

## 2. Initialize and Push

From the project root:

```bash
git init
git add .
git commit -m "Build mission-critical incident management system"
git branch -M main
git remote add origin https://github.com/<your-username>/zeotap-incident-management-system.git
git push -u origin main
```

## 3. Regenerate Submission PDF with GitHub Link

After pushing, regenerate the PDF with the real repository URL:

```bash
GITHUB_URL=https://github.com/<your-username>/zeotap-incident-management-system npm run pdf
```

On PowerShell:

```powershell
$env:GITHUB_URL="https://github.com/<your-username>/zeotap-incident-management-system"
npm run pdf
```

## 4. PDF Filename

The requested email format contains `/`, which is not allowed in Windows filenames. This repository generates:

```text
Chitransh - Infrastructure - SRE Intern Assignment.pdf
```

If your full name includes a surname, rename the PDF before submission, for example:

```text
Chitransh <Surname> - Infrastructure - SRE Intern Assignment.pdf
```

## 5. Final Email Checklist

- GitHub repository contains backend, frontend, docs, Docker Compose, build scripts, and sample data.
- `README.md` includes setup, architecture, backpressure, and non-functional notes.
- PDF includes the GitHub link.
- PDF is attached as the assignment submission.
- Submit before 6 May 2026.
