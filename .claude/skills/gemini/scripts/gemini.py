#!/usr/bin/env python3
"""Minimal Gemini API client (stdlib only).

Usage:
  gemini.py "prompt"                      # prompt as argument
  echo "prompt" | gemini.py               # prompt from stdin
  gemini.py -f file.py "Review this"      # attach file(s) as context
  gemini.py -m gemini-2.5-pro "..."       # choose model
  gemini.py --list-models                 # show available models

API key: GEMINI_API_KEY env var. In Claude Code cloud sessions the key is
injected by the network proxy, so a placeholder value is used if unset.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def request(method, path, body=None):
    key = os.environ.get("GEMINI_API_KEY", "placeholder-injected-by-proxy")
    req = urllib.request.Request(
        f"{API}/{path}",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"Gemini API error {e.code}: {e.read().decode(errors='replace')}")


def list_models():
    data = request("GET", "models?pageSize=1000")
    for m in data.get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"].removeprefix("models/"), "-", m.get("displayName", ""))


def generate(model, prompt, files, system, temperature):
    parts = []
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            parts.append({"text": f"--- File: {path} ---\n{fh.read()}"})
    parts.append({"text": prompt})
    body = {"contents": [{"role": "user", "parts": parts}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if temperature is not None:
        body["generationConfig"] = {"temperature": temperature}
    data = request("POST", f"models/{model}:generateContent", body)
    candidates = data.get("candidates") or []
    if not candidates:
        sys.exit(f"No response: {json.dumps(data.get('promptFeedback', data))}")
    text = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []))
    print(text)


def main():
    ap = argparse.ArgumentParser(description="Ask Gemini")
    ap.add_argument("prompt", nargs="?", help="prompt (or read from stdin)")
    ap.add_argument("-m", "--model", default=DEFAULT_MODEL)
    ap.add_argument("-f", "--file", action="append", default=[], help="attach file as context")
    ap.add_argument("-s", "--system", help="system instruction")
    ap.add_argument("-t", "--temperature", type=float)
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()

    if args.list_models:
        return list_models()
    prompt = args.prompt if args.prompt else sys.stdin.read()
    if not prompt.strip():
        ap.error("empty prompt")
    generate(args.model, prompt, args.file, args.system, args.temperature)


if __name__ == "__main__":
    main()
