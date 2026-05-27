# Flask Prayer App

A social prayer tracking web application built with Flask and PostgreSQL.

## What It Does

Users log in to see a daily prayer feed — their own requests plus their 
friends' public prayers. Each prayer can be ticked off as prayed each day.

Key features:
- User authentication (register, login, logout)
- Create prayer requests as public or private
- Friends' public prayers appear in your feed
- Mark prayers as answered — the app then prompts daily gratitude 
  reminders for that answered prayer for one week
- Persistent tracking via PostgreSQL

## Stack

- Python / Flask
- PostgreSQL
- Docker / Docker Compose
- Gunicorn
- Deployed on AWS EC2

## Running Locally

```bash
docker-compose up --build
```

App runs at `http://localhost:5000`

## Background

Built as a personal project to learn Flask, Docker, and AWS deployment. 
The answered-prayer gratitude feature was the core design motivation — 
shifting focus from requests to thankfulness over time.
