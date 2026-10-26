const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function parseError(response) {
  try {
    const payload = await response.json();
    const detail = payload?.detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
    if (typeof detail === "string") return detail;
    return `Request failed: ${response.status} ${response.statusText}`;
  } catch {
    return `Request failed: ${response.status} ${response.statusText}`;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) throw new ApiError(await parseError(response), response.status, null);
  return response.json();
}

export function getJson(path) {
  return request(path, { headers: { Accept: "application/json" } });
}

function jsonOptions(method, body) {
  return {
    method,
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function postJson(path, body) {
  return request(path, jsonOptions("POST", body));
}

export function patchJson(path, body) {
  return request(path, jsonOptions("PATCH", body));
}

export function postForm(path, formData) {
  return request(path, { method: "POST", body: formData });
}

export async function fetchJson(path) {
  return getJson(path);
}

export { API_BASE };
