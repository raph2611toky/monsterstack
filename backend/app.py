from flask import Flask, send_file, jsonify, render_template_string
import hashlib
import io
import json
import random
from PIL import Image, ImageDraw

app = Flask(__name__)

# ─── OpenAPI spec ────────────────────────────────────────────────────────────
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Monster Stack — Backend API",
        "description": "Backend déterministe de génération d'avatars monstres basés sur une chaîne de caractères. Utilisé par le frontend Flask via Redis cache.",
        "version": "1.0.0",
        "contact": {"name": "ENI Grid Cluster", "email": "jennyscaladydi@gmail.com"}
    },
    "servers": [{"url": "/", "description": "Serveur local"}],
    "tags": [
        {"name": "Monsters", "description": "Génération d'avatars"},
        {"name": "Health",   "description": "Monitoring du service"}
    ],
    "paths": {
        "/monster/{name}": {
            "get": {
                "tags": ["Monsters"],
                "summary": "Générer un avatar monstre",
                "description": "Génère une image PNG déterministe (200×200px) pour le nom donné. Le même nom produit toujours la même image (basé sur MD5 seed).",
                "operationId": "getMonster",
                "parameters": [{
                    "name": "name",
                    "in": "path",
                    "required": True,
                    "description": "Nom du monstre (ex: Globglob)",
                    "schema": {"type": "string", "example": "Globglob", "minLength": 1, "maxLength": 64}
                }],
                "responses": {
                    "200": {
                        "description": "Image PNG du monstre",
                        "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}
                    },
                    "400": {"description": "Nom invalide ou vide"}
                }
            }
        },
        "/health": {
            "get": {
                "tags": ["Health"],
                "summary": "Vérification santé du service",
                "operationId": "getHealth",
                "responses": {
                    "200": {
                        "description": "Service opérationnel",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string", "example": "ok"},
                                        "service": {"type": "string", "example": "monster-backend"},
                                        "version": {"type": "string", "example": "1.0.0"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/api/spec": {
            "get": {
                "tags": ["Health"],
                "summary": "Spécification OpenAPI JSON",
                "operationId": "getSpec",
                "responses": {
                    "200": {"description": "Spécification OpenAPI 3.0"}
                }
            }
        }
    }
}

SWAGGER_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Monster API — Docs</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin:0; padding:0; }

    :root {
      --bg: #F5F0E8;
      --ink: #1A1410;
      --ink-muted: #6B6055;
      --accent: #E8440A;
      --accent-pale: #FAE8E0;
      --green: #166534;
      --green-bg: #f0fdf4;
      --green-border: #22c55e;
      --blue: #1e40af;
      --blue-bg: #eff6ff;
      --blue-border: #3b82f6;
      --card: #FFFDF8;
      --border: #D4C8B8;
      --mono: 'DM Mono', monospace;
      --sans: 'Syne', sans-serif;
      --radius: 4px;
    }

    body {
      font-family: var(--sans);
      background: var(--bg);
      color: var(--ink);
      min-height: 100vh;
    }

    body::before {
      content: '';
      position: fixed; inset:0;
      background-image:
        repeating-linear-gradient(0deg, transparent, transparent 39px, var(--border) 39px, var(--border) 40px),
        repeating-linear-gradient(90deg, transparent, transparent 39px, var(--border) 39px, var(--border) 40px);
      opacity: 0.2; pointer-events:none; z-index:0;
    }

    /* ── TOPBAR ── */
    .topbar {
      position: sticky; top:0; z-index:100;
      background: var(--ink);
      padding: 0 48px;
      display: flex; align-items: center; height: 56px; gap: 24px;
      border-bottom: 2px solid var(--accent);
    }

    .topbar-logo {
      font-size: 14px; font-weight: 800;
      color: white; letter-spacing: -0.01em;
    }

    .topbar-logo span { color: var(--accent); }

    .topbar-badge {
      font-size: 10px; font-family: var(--mono);
      background: var(--accent); color: white;
      padding: 3px 8px; letter-spacing: 0.08em;
    }

    .topbar-ver {
      font-size: 11px; font-family: var(--mono);
      color: rgba(255,255,255,0.4);
    }

    .topbar-link {
      margin-left: auto;
      font-size: 12px; font-family: var(--mono);
      color: rgba(255,255,255,0.5);
      text-decoration: none;
      letter-spacing: 0.05em;
      transition: color 0.2s;
    }
    .topbar-link:hover { color: var(--accent); }

    /* ── LAYOUT ── */
    .layout {
      position: relative; z-index:1;
      display: grid;
      grid-template-columns: 260px 1fr;
      max-width: 1200px;
      margin: 0 auto;
      min-height: calc(100vh - 56px);
    }

    /* ── SIDEBAR ── */
    .sidebar {
      padding: 40px 24px;
      border-right: 1px solid var(--border);
      position: sticky; top: 56px;
      height: calc(100vh - 56px);
      overflow-y: auto;
    }

    .sidebar-section {
      margin-bottom: 32px;
    }

    .sidebar-heading {
      font-size: 10px; font-family: var(--mono);
      color: var(--ink-muted); letter-spacing: 0.15em;
      text-transform: uppercase; margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }

    .sidebar-item {
      display: flex; align-items: center; gap: 10px;
      padding: 8px 10px; cursor: pointer;
      border-radius: var(--radius);
      font-size: 13px; font-family: var(--mono);
      color: var(--ink-muted);
      transition: background 0.15s, color 0.15s;
      text-decoration: none;
      margin-bottom: 2px;
    }

    .sidebar-item:hover { background: var(--accent-pale); color: var(--accent); }
    .sidebar-item.active { background: var(--accent-pale); color: var(--accent); }

    .method-pill-sm {
      font-size: 9px; font-weight: 500; font-family: var(--mono);
      padding: 2px 6px; border-radius: 2px;
      min-width: 34px; text-align: center;
    }
    .get-sm  { background: var(--green-bg);  color: var(--green);  }

    .sidebar-info {
      margin-top: auto;
      padding: 16px;
      background: var(--card);
      border: 1px solid var(--border);
    }

    .sidebar-info-title {
      font-size: 11px; font-weight: 700;
      color: var(--ink); margin-bottom: 6px;
    }

    .sidebar-info-text {
      font-size: 11px; font-family: var(--mono);
      color: var(--ink-muted); line-height: 1.6;
    }

    /* ── CONTENT ── */
    .content {
      padding: 48px 56px;
    }

    /* ── API INFO HEADER ── */
    .api-header {
      margin-bottom: 56px;
    }

    .api-header-top {
      display: flex; align-items: flex-start;
      justify-content: space-between; margin-bottom: 20px;
    }

    .api-title {
      font-size: 36px; font-weight: 800;
      letter-spacing: -0.03em; line-height: 1;
      color: var(--ink);
    }

    .api-title .accent { color: var(--accent); }

    .api-badges {
      display: flex; gap: 8px; flex-wrap: wrap;
      margin-top: 12px;
    }

    .badge {
      font-size: 10px; font-family: var(--mono);
      padding: 4px 10px; border: 1.5px solid;
      letter-spacing: 0.06em;
    }

    .badge-green  { border-color: var(--green-border); color: var(--green); background: var(--green-bg); }
    .badge-accent { border-color: var(--accent); color: var(--accent); background: var(--accent-pale); }
    .badge-neutral{ border-color: var(--border); color: var(--ink-muted); background: transparent; }

    .api-description {
      font-size: 15px; color: var(--ink-muted);
      line-height: 1.7; max-width: 600px;
      font-family: var(--mono);
    }

    .servers-row {
      display: flex; gap: 10px; flex-wrap: wrap;
      margin-top: 16px;
    }

    .server-tag {
      font-size: 12px; font-family: var(--mono);
      padding: 6px 14px; background: var(--card);
      border: 1px solid var(--border); color: var(--ink-muted);
      display: flex; align-items: center; gap: 8px;
    }

    .server-tag .dot { width:6px; height:6px; border-radius:50%; background: var(--green-border); }

    /* ── SECTION ── */
    .section { margin-bottom: 40px; }

    .section-tag {
      display: inline-flex; align-items: center; gap: 8px;
      font-size: 11px; font-family: var(--mono); font-weight: 500;
      color: var(--ink-muted); letter-spacing: 0.12em;
      text-transform: uppercase;
      border-bottom: 2px solid var(--accent);
      padding-bottom: 4px; margin-bottom: 24px;
    }

    /* ── ENDPOINT CARD ── */
    .endpoint-card {
      background: var(--card);
      border: 1.5px solid var(--border);
      margin-bottom: 20px;
      overflow: hidden;
      transition: border-color 0.2s;
    }

    .endpoint-card:hover { border-color: var(--accent); }

    .endpoint-header {
      display: flex; align-items: center; gap: 16px;
      padding: 20px 24px; cursor: pointer;
      user-select: none;
    }

    .method-pill {
      font-size: 11px; font-weight: 700; font-family: var(--mono);
      padding: 5px 12px; min-width: 56px; text-align: center;
      letter-spacing: 0.06em;
    }
    .get  { background: var(--green-bg);  color: var(--green);  border: 1.5px solid var(--green-border); }
    .post { background: var(--blue-bg);   color: var(--blue);   border: 1.5px solid var(--blue-border); }

    .endpoint-path {
      font-family: var(--mono); font-size: 15px;
      color: var(--ink); font-weight: 500;
      flex: 1;
    }

    .endpoint-path .param { color: var(--accent); }

    .endpoint-summary {
      font-size: 13px; color: var(--ink-muted);
      font-family: var(--mono);
      margin-left: auto;
      max-width: 260px;
      text-align: right;
    }

    .endpoint-chevron {
      font-size: 14px; color: var(--ink-muted);
      transition: transform 0.25s;
      margin-left: 8px;
    }

    .endpoint-card.open .endpoint-chevron { transform: rotate(180deg); }

    .endpoint-body {
      display: none;
      padding: 0 24px 28px;
      border-top: 1px solid var(--border);
    }

    .endpoint-card.open .endpoint-body { display: block; }

    .endpoint-description {
      padding: 20px 0 16px;
      font-size: 13px; font-family: var(--mono);
      color: var(--ink-muted); line-height: 1.7;
    }

    /* ── PARAMS TABLE ── */
    .param-section-label {
      font-size: 11px; font-family: var(--mono);
      font-weight: 500; color: var(--ink);
      letter-spacing: 0.08em; text-transform: uppercase;
      margin: 20px 0 12px;
    }

    .params-table {
      width: 100%; border-collapse: collapse;
      font-size: 13px;
    }

    .params-table th {
      font-size: 10px; font-family: var(--mono);
      color: var(--ink-muted); font-weight: 500;
      letter-spacing: 0.1em; text-transform: uppercase;
      text-align: left; padding: 8px 12px;
      border-bottom: 1px solid var(--border);
    }

    .params-table td {
      padding: 12px 12px;
      border-bottom: 1px solid rgba(212,200,184,0.4);
      vertical-align: top;
    }

    .params-table tr:last-child td { border-bottom: none; }

    .param-name {
      font-family: var(--mono); font-size: 13px;
      color: var(--ink); font-weight: 500;
    }

    .param-required {
      font-size: 9px; font-family: var(--mono);
      background: var(--accent-pale); color: var(--accent);
      padding: 2px 6px; margin-left: 8px;
      vertical-align: middle;
    }

    .param-type {
      font-family: var(--mono); font-size: 12px;
      color: var(--blue); background: var(--blue-bg);
      padding: 2px 8px;
    }

    .param-in {
      font-family: var(--mono); font-size: 11px;
      color: var(--ink-muted);
    }

    .param-desc {
      font-size: 12px; font-family: var(--mono);
      color: var(--ink-muted); line-height: 1.5;
    }

    .param-example {
      font-family: var(--mono); font-size: 11px;
      color: var(--accent);
    }

    /* ── RESPONSES ── */
    .response-item {
      display: flex; align-items: flex-start; gap: 16px;
      padding: 14px 16px; background: var(--bg);
      border: 1px solid var(--border); margin-bottom: 8px;
    }

    .response-code {
      font-family: var(--mono); font-size: 14px; font-weight: 700;
      min-width: 48px;
    }

    .response-code.r200 { color: var(--green); }
    .response-code.r400 { color: #dc2626; }

    .response-desc {
      font-size: 13px; font-family: var(--mono);
      color: var(--ink-muted);
    }

    .response-content-type {
      font-size: 11px; font-family: var(--mono);
      color: var(--ink-muted);
      margin-top: 4px;
      padding: 2px 8px;
      background: var(--card);
      border: 1px solid var(--border);
      display: inline-block;
    }

    /* ── TRY IT ── */
    .try-section {
      margin-top: 24px; padding-top: 20px;
      border-top: 1px dashed var(--border);
    }

    .try-label {
      font-size: 11px; font-family: var(--mono);
      font-weight: 500; color: var(--ink);
      letter-spacing: 0.1em; text-transform: uppercase;
      margin-bottom: 14px;
    }

    .try-form {
      display: flex; gap: 10px; align-items: flex-end;
      flex-wrap: wrap;
    }

    .try-input-group { flex: 1; min-width: 200px; }
    .try-input-label {
      display: block; font-size: 10px; font-family: var(--mono);
      color: var(--ink-muted); letter-spacing: 0.08em;
      text-transform: uppercase; margin-bottom: 6px;
    }

    .try-input {
      width: 100%; font-family: var(--mono); font-size: 14px;
      color: var(--ink); background: var(--card);
      border: 1.5px solid var(--border);
      padding: 10px 14px; outline: none;
      transition: border-color 0.2s;
    }

    .try-input:focus { border-color: var(--accent); }

    .try-btn {
      background: var(--accent); color: white;
      border: none; font-family: var(--sans);
      font-size: 13px; font-weight: 700;
      padding: 11px 24px; cursor: pointer;
      letter-spacing: 0.04em;
      transition: background 0.2s;
    }

    .try-btn:hover { background: #c73608; }
    .try-btn:active { transform: translateY(1px); }

    .try-result {
      margin-top: 16px;
      display: none;
    }

    .try-result.visible { display: block; }

    .try-result-header {
      display: flex; align-items: center; gap: 12px;
      margin-bottom: 10px;
      font-size: 11px; font-family: var(--mono);
      color: var(--ink-muted);
    }

    .try-status {
      font-weight: 500; color: var(--green);
    }

    .try-result-body {
      background: var(--card); border: 1px solid var(--border);
      padding: 20px; text-align: center;
    }

    .try-result-body img {
      width: 160px; height: 160px;
      image-rendering: pixelated;
    }

    .try-result-body.error {
      color: #dc2626; font-family: var(--mono);
      font-size: 13px; text-align: left;
    }

    .try-result-body.json-view {
      text-align: left;
    }

    .json-pre {
      font-family: var(--mono); font-size: 12px;
      color: var(--ink); line-height: 1.8;
      white-space: pre-wrap;
    }

    .json-key   { color: var(--accent); }
    .json-str   { color: var(--green); }

    /* ── SCHEMA BOX ── */
    .schema-box {
      background: var(--bg); border: 1px solid var(--border);
      padding: 16px 20px; margin-top: 12px;
      font-family: var(--mono); font-size: 12px;
      line-height: 1.8;
    }

    /* ── RESPONSIVE ── */
    @media (max-width: 900px) {
      .layout { grid-template-columns: 1fr; }
      .sidebar { display: none; }
      .content { padding: 32px 24px; }
    }

    @keyframes fade-in {
      from { opacity:0; transform: translateY(8px); }
      to   { opacity:1; transform: translateY(0); }
    }
  </style>
</head>
<body>

  <!-- TOPBAR -->
  <nav class="topbar">
    <span class="topbar-logo">Monster<span>API</span></span>
    <span class="topbar-badge">OpenAPI 3.0</span>
    <span class="topbar-ver">v1.0.0</span>
    <a href="/" class="topbar-link">← Frontend</a>
  </nav>

  <div class="layout">

    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sidebar-section">
        <p class="sidebar-heading">Endpoints</p>
        <a class="sidebar-item" href="#monster-get" onclick="scrollTo('monster-get')">
          <span class="method-pill-sm get-sm">GET</span>
          /monster/{name}
        </a>
        <a class="sidebar-item" href="#health-get" onclick="scrollTo('health-get')">
          <span class="method-pill-sm get-sm">GET</span>
          /health
        </a>
        <a class="sidebar-item" href="#spec-get" onclick="scrollTo('spec-get')">
          <span class="method-pill-sm get-sm">GET</span>
          /api/spec
        </a>
      </div>

      <div class="sidebar-section">
        <p class="sidebar-heading">Ressources</p>
        <a class="sidebar-item" href="/api/spec" target="_blank">
          Spec JSON ↗
        </a>
        <a class="sidebar-item" href="/health" target="_blank">
          Santé du service ↗
        </a>
      </div>

      <div style="margin-top: 32px;">
        <div class="sidebar-info">
          <p class="sidebar-info-title">Monster Stack</p>
          <p class="sidebar-info-text">
            Backend de génération d'avatars.<br>
            MD5 seed · Pillow · Flask 3.0<br>
            Déployé sur GKE
          </p>
        </div>
      </div>
    </aside>

    <!-- CONTENT -->
    <main class="content">

      <!-- API HEADER -->
      <div class="api-header">
        <div class="api-header-top">
          <div>
            <h1 class="api-title">Monster<br><span class="accent">Backend</span></h1>
            <div class="api-badges">
              <span class="badge badge-green">● Opérationnel</span>
              <span class="badge badge-accent">OpenAPI 3.0</span>
              <span class="badge badge-neutral">v1.0.0</span>
              <span class="badge badge-neutral">Port 8080</span>
            </div>
          </div>
        </div>
        <p class="api-description">
          Backend déterministe de génération d'avatars monstres.<br>
          Chaque nom produit toujours la même image via MD5 seed.
        </p>
        <div class="servers-row">
          <div class="server-tag">
            <span class="dot"></span>
            http://localhost:8080
          </div>
          <div class="server-tag">
            <span class="dot"></span>
            http://backend:8080 (Docker)
          </div>
        </div>
      </div>

      <!-- MONSTERS TAG -->
      <div class="section">
        <div class="section-tag">
          🐾 Monsters
        </div>

        <!-- GET /monster/{name} -->
        <div class="endpoint-card" id="monster-get">
          <div class="endpoint-header" onclick="toggleCard(this)">
            <span class="method-pill get">GET</span>
            <span class="endpoint-path">/monster/<span class="param">{name}</span></span>
            <span class="endpoint-summary">Générer un avatar monstre</span>
            <span class="endpoint-chevron">▾</span>
          </div>
          <div class="endpoint-body">
            <p class="endpoint-description">
              Génère une image PNG 200×200 px déterministe pour le nom donné.<br>
              Le même nom produit <strong>toujours</strong> la même image (seed = MD5(name)).
            </p>

            <p class="param-section-label">Paramètres</p>
            <table class="params-table">
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>Emplacement</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Exemple</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <span class="param-name">name</span>
                    <span class="param-required">requis</span>
                  </td>
                  <td><span class="param-in">path</span></td>
                  <td><span class="param-type">string</span></td>
                  <td><span class="param-desc">Nom du monstre (1–64 chars)</span></td>
                  <td><span class="param-example">Globglob</span></td>
                </tr>
              </tbody>
            </table>

            <p class="param-section-label">Réponses</p>
            <div class="response-item">
              <span class="response-code r200">200</span>
              <div>
                <div class="response-desc">Image PNG du monstre générée avec succès</div>
                <span class="response-content-type">image/png</span>
              </div>
            </div>
            <div class="response-item">
              <span class="response-code r400">400</span>
              <div class="response-desc">Nom invalide ou vide</div>
            </div>

            <!-- TRY IT -->
            <div class="try-section">
              <p class="try-label">⚡ Essayer</p>
              <div class="try-form">
                <div class="try-input-group">
                  <label class="try-input-label" for="try-name">name (path)</label>
                  <input class="try-input" type="text" id="try-name" placeholder="Globglob" value="Globglob">
                </div>
                <button class="try-btn" onclick="tryMonster()">Exécuter</button>
              </div>
              <div class="try-result" id="try-result-monster">
                <div class="try-result-header">
                  <span>Réponse ·</span>
                  <span class="try-status" id="try-status-monster">200 OK</span>
                  <span id="try-time-monster"></span>
                </div>
                <div class="try-result-body" id="try-body-monster"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- HEALTH TAG -->
      <div class="section">
        <div class="section-tag">
          🔧 Health
        </div>

        <!-- GET /health -->
        <div class="endpoint-card" id="health-get">
          <div class="endpoint-header" onclick="toggleCard(this)">
            <span class="method-pill get">GET</span>
            <span class="endpoint-path">/health</span>
            <span class="endpoint-summary">Vérification santé</span>
            <span class="endpoint-chevron">▾</span>
          </div>
          <div class="endpoint-body">
            <p class="endpoint-description">
              Retourne le statut de santé du service backend. Utilisé par les probes Kubernetes (liveness / readiness).
            </p>

            <p class="param-section-label">Réponses</p>
            <div class="response-item">
              <span class="response-code r200">200</span>
              <div>
                <div class="response-desc">Service opérationnel</div>
                <span class="response-content-type">application/json</span>
              </div>
            </div>

            <div class="schema-box">
              <span class="json-key">"status"</span>: <span class="json-str">"ok"</span>,<br>
              <span class="json-key">"service"</span>: <span class="json-str">"monster-backend"</span>,<br>
              <span class="json-key">"version"</span>: <span class="json-str">"1.0.0"</span>
            </div>

            <div class="try-section">
              <p class="try-label">⚡ Essayer</p>
              <div class="try-form">
                <button class="try-btn" onclick="tryHealth()">Exécuter</button>
              </div>
              <div class="try-result" id="try-result-health">
                <div class="try-result-header">
                  <span>Réponse ·</span>
                  <span class="try-status" id="try-status-health">200 OK</span>
                  <span id="try-time-health"></span>
                </div>
                <div class="try-result-body json-view" id="try-body-health"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- GET /api/spec -->
        <div class="endpoint-card" id="spec-get">
          <div class="endpoint-header" onclick="toggleCard(this)">
            <span class="method-pill get">GET</span>
            <span class="endpoint-path">/api/spec</span>
            <span class="endpoint-summary">Spec OpenAPI JSON</span>
            <span class="endpoint-chevron">▾</span>
          </div>
          <div class="endpoint-body">
            <p class="endpoint-description">
              Retourne la spécification OpenAPI 3.0 complète au format JSON.
            </p>
            <div class="response-item">
              <span class="response-code r200">200</span>
              <div>
                <div class="response-desc">Spécification OpenAPI 3.0.3 JSON</div>
                <span class="response-content-type">application/json</span>
              </div>
            </div>

            <div class="try-section">
              <p class="try-label">⚡ Essayer</p>
              <div class="try-form">
                <button class="try-btn" onclick="trySpec()">Exécuter</button>
              </div>
              <div class="try-result" id="try-result-spec">
                <div class="try-result-header">
                  <span>Réponse ·</span>
                  <span class="try-status" id="try-status-spec">200 OK</span>
                  <span id="try-time-spec"></span>
                </div>
                <div class="try-result-body json-view" id="try-body-spec"></div>
              </div>
            </div>
          </div>
        </div>

      </div><!-- end health section -->
    </main>
  </div>

  <script>
    function toggleCard(header) {
      const card = header.closest('.endpoint-card');
      card.classList.toggle('open');
    }

    async function tryMonster() {
      const name = document.getElementById('try-name').value.trim() || 'Globglob';
      const resultDiv = document.getElementById('try-result-monster');
      const bodyDiv   = document.getElementById('try-body-monster');
      const statusEl  = document.getElementById('try-status-monster');
      const timeEl    = document.getElementById('try-time-monster');

      bodyDiv.innerHTML = '<span style="font-family:var(--mono);font-size:12px;color:var(--ink-muted)">Chargement...</span>';
      resultDiv.classList.add('visible');

      const t0 = performance.now();
      try {
        const resp = await fetch(`/monster/${encodeURIComponent(name)}`);
        const ms = Math.round(performance.now() - t0);
        statusEl.textContent = resp.status + ' ' + (resp.ok ? 'OK' : 'Erreur');
        statusEl.style.color = resp.ok ? 'var(--green)' : '#dc2626';
        timeEl.textContent = `· ${ms}ms`;

        if (resp.ok) {
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          bodyDiv.innerHTML = `<img src="${url}" alt="Monster ${name}">
            <p style="margin-top:12px;font-family:var(--mono);font-size:12px;color:var(--ink-muted)">
              Content-Type: image/png · ${Math.round(blob.size/1024)}KB
            </p>`;
        } else {
          bodyDiv.classList.add('error');
          bodyDiv.textContent = 'Erreur: ' + resp.status;
        }
      } catch(e) {
        bodyDiv.classList.add('error');
        bodyDiv.textContent = 'Erreur réseau: ' + e.message;
      }
    }

    async function tryHealth() {
      const resultDiv = document.getElementById('try-result-health');
      const bodyDiv   = document.getElementById('try-body-health');
      const statusEl  = document.getElementById('try-status-health');
      const timeEl    = document.getElementById('try-time-health');
      resultDiv.classList.add('visible');
      const t0 = performance.now();
      try {
        const resp = await fetch('/health');
        const ms = Math.round(performance.now() - t0);
        const data = await resp.json();
        statusEl.textContent = resp.status + ' OK';
        timeEl.textContent = `· ${ms}ms`;
        bodyDiv.innerHTML = `<pre class="json-pre">${syntaxHighlight(JSON.stringify(data, null, 2))}</pre>`;
      } catch(e) {
        bodyDiv.textContent = 'Erreur: ' + e.message;
      }
    }

    async function trySpec() {
      const resultDiv = document.getElementById('try-result-spec');
      const bodyDiv   = document.getElementById('try-body-spec');
      const statusEl  = document.getElementById('try-status-spec');
      const timeEl    = document.getElementById('try-time-spec');
      resultDiv.classList.add('visible');
      const t0 = performance.now();
      try {
        const resp = await fetch('/api/spec');
        const ms = Math.round(performance.now() - t0);
        const data = await resp.json();
        statusEl.textContent = resp.status + ' OK';
        timeEl.textContent = `· ${ms}ms`;
        const preview = {openapi: data.openapi, info: data.info, paths: Object.keys(data.paths)};
        bodyDiv.innerHTML = `<pre class="json-pre">${syntaxHighlight(JSON.stringify(preview, null, 2))}</pre>
          <p style="margin-top:12px;font-family:var(--mono);font-size:11px;color:var(--ink-muted)">
            (résumé — <a href="/api/spec" target="_blank" style="color:var(--accent)">voir spec complète ↗</a>)
          </p>`;
      } catch(e) {
        bodyDiv.textContent = 'Erreur: ' + e.message;
      }
    }

    function syntaxHighlight(json) {
      return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, match => {
        if (/^"/.test(match)) {
          if (/:$/.test(match)) return `<span class="json-key">${match}</span>`;
          return `<span class="json-str">${match}</span>`;
        }
        return match;
      });
    }

    // Open monster endpoint by default
    document.getElementById('monster-get').classList.add('open');
  </script>

</body>
</html>"""


def generate_monster(name: str) -> bytes:
    seed = int(hashlib.md5(name.encode()).hexdigest(), 16)
    rng  = random.Random(seed)
    size = 200
    img  = Image.new("RGB", (size, size), color=(250, 248, 242))
    draw = ImageDraw.Draw(img)

    r, g, b = rng.randint(60,220), rng.randint(60,220), rng.randint(60,220)
    body_color = (r, g, b)

    # Body
    draw.ellipse([35, 55, 165, 175], fill=body_color)

    # Eyes
    for ex in [75, 125]:
        draw.ellipse([ex-16, 78, ex+16, 112], fill=(255,255,255))
        px = ex + rng.randint(-6, 6)
        py = 95 + rng.randint(-5, 5)
        draw.ellipse([px-7, py-7, px+7, py+7], fill=(20,20,20))
        draw.ellipse([px-2, py-4, px+2, py-1], fill=(255,255,255))

    # Mouth
    mx = [(65+rng.randint(-5,5), 145),
          (100, 160+rng.randint(-8,8)),
          (135+rng.randint(-5,5), 145)]
    draw.line(mx, fill=(40,25,15), width=3)

    # Teeth
    if rng.random() > 0.4:
        for tx in [85, 100, 115]:
            draw.polygon([(tx-5,145),(tx+5,145),(tx,158)], fill=(255,255,240))

    # Horns / antennae
    hn = rng.randint(1, 3)
    for i in range(hn):
        hx = 55 + i * 45
        jitter = rng.randint(-8, 8)
        draw.polygon([(hx+jitter,55),(hx-14+jitter,22),(hx+14+jitter,22)], fill=body_color)
        draw.polygon([(hx+jitter,55),(hx-14+jitter,22),(hx+14+jitter,22)],
                     outline=(max(0,r-40),max(0,g-40),max(0,b-40)), width=1)

    # Spots / texture
    for _ in range(rng.randint(0, 5)):
        sx, sy = rng.randint(45,155), rng.randint(80,160)
        sr = rng.randint(4,10)
        sc = (min(255,r+40), min(255,g+40), min(255,b+40))
        draw.ellipse([sx-sr,sy-sr,sx+sr,sy+sr], fill=sc)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/monster/<name>")
def monster(name: str):
    if not name or len(name) > 64:
        return {"error": "Nom invalide"}, 400
    img_bytes = generate_monster(name)
    return send_file(io.BytesIO(img_bytes), mimetype="image/png")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "monster-backend", "version": "1.0.0"})


@app.route("/api/spec")
def spec():
    return jsonify(OPENAPI_SPEC)


@app.route("/docs")
@app.route("/swagger")
def swagger_ui():
    return render_template_string(SWAGGER_HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)