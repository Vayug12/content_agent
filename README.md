---
title: VayugAI API
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# VayugAI API

REST API wrapper for VayugAI content generation agents.

## Features

- Topic selection
- Research generation
- Script writing
- Video editing
- SEO metadata generation
- Analytics

## API Endpoints

- `GET /health` - Health check
- `GET /stats` - Pipeline statistics
- `POST /topic` - Select topic
- `POST /research` - Research topic
- `POST /script` - Write script
- `POST /pipeline/run` - Run full pipeline

## Environment Variables

- `GROQ_API_KEY` - Groq API key
- `PEXELS_API_KEY` - Pexels API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon key
