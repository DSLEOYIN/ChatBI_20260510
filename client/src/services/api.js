const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function sendChat(payload) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }
  return response.json();
}

export async function streamChat(payload, onEvent) {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok || !response.body) {
    throw new Error(`Stream request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      onEvent(JSON.parse(line.slice(5).trim()));
    }
  }
}

export async function listConversations(userId = "demo_user") {
  const response = await fetch(`${API_BASE}/conversations?user_id=${encodeURIComponent(userId)}`);
  if (!response.ok) return [];
  return response.json();
}

export async function getConversation(id) {
  const response = await fetch(`${API_BASE}/conversations/${id}`);
  if (!response.ok) {
    throw new Error(`Conversation not found: ${id}`);
  }
  return response.json();
}

export async function deleteConversation(id) {
  const response = await fetch(`${API_BASE}/conversations/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`Delete failed: ${id}`);
  }
  return response.json();
}

export async function getSkills() {
  const response = await fetch(`${API_BASE}/config/skills`);
  if (!response.ok) return [];
  return response.json();
}

export async function getStreamContract() {
  const response = await fetch(`${API_BASE}/config/stream-contract`);
  if (!response.ok) return null;
  return response.json();
}

export async function getMockContract() {
  const response = await fetch(`${API_BASE}/config/mock-contract`);
  if (!response.ok) return null;
  return response.json();
}

export async function pinConversation(id, pinned) {
  const response = await fetch(`${API_BASE}/conversations/${id}/pin?pinned=${pinned ? "true" : "false"}`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Pin failed: ${id}`);
  }
  return response.json();
}

export function absoluteApiPath(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_BASE.replace(/\/api$/, "")}${path}`;
}
