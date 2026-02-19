import { useState, useEffect, useCallback } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from "recharts";
import { Shield, Activity, Zap, DollarSign, Plus, Trash2, Edit3, Eye, EyeOff, ChevronDown, ChevronUp, X, Check, AlertTriangle, Clock, Server, RefreshCw, Settings, BarChart3, List, Lock, Search, Mic, Video, GitBranch, Cloud, HardDrive, Globe, Key, FileText } from "lucide-react";

// --- Service Templates ---
const SERVICE_TEMPLATES = {
  ollama:       { name: "Ollama (Local)",      category: "LLM",            icon: "HardDrive", color: "#34d399", fields: { baseUrl: true, apiKey: false, token: false, credPath: false }, defaults: { baseUrl: "http://127.0.0.1:11434" }, hint: "Local inference server — no authentication required" },
  openai:       { name: "OpenAI",              category: "LLM",            icon: "Cloud",     color: "#22d3ee", fields: { baseUrl: true, apiKey: true,  token: false, credPath: false }, defaults: { baseUrl: "https://api.openai.com/v1" }, hint: "Requires an API key from platform.openai.com" },
  anthropic:    { name: "Anthropic",           category: "LLM",            icon: "Cloud",     color: "#a78bfa", fields: { baseUrl: true, apiKey: true,  token: false, credPath: false }, defaults: { baseUrl: "https://api.anthropic.com/v1" }, hint: "Requires an API key from console.anthropic.com" },
  elevenlabs:   { name: "ElevenLabs",          category: "Media / Audio",  icon: "Mic",       color: "#f472b6", fields: { baseUrl: false, apiKey: true,  token: false, credPath: false }, defaults: { baseUrl: "https://api.elevenlabs.io/v1" }, hint: "Text-to-speech and voice cloning API" },
  sora:         { name: "Sora 2 (OpenAI)",     category: "Media / Video",  icon: "Video",     color: "#fb923c", fields: { baseUrl: false, apiKey: true,  token: false, credPath: false }, defaults: { baseUrl: "https://api.openai.com/v1" }, hint: "Uses your OpenAI API key — video generation endpoints" },
  kie:          { name: "Kie.ai",              category: "Media / Video",  icon: "Video",     color: "#38bdf8", fields: { baseUrl: false, apiKey: true,  token: false, credPath: false }, defaults: { baseUrl: "https://api.kie.ai" }, hint: "Cost-effective video generation — $0.24/5s" },
  github:       { name: "GitHub",              category: "Git / DevOps",   icon: "GitBranch", color: "#e2e8f0", fields: { baseUrl: false, apiKey: false, token: true,  credPath: false }, defaults: { baseUrl: "https://api.github.com" }, hint: "Personal Access Token with repo + workflow scopes" },
  gitlab:       { name: "GitLab",              category: "Git / DevOps",   icon: "GitBranch", color: "#fb923c", fields: { baseUrl: true, apiKey: false, token: true,  credPath: false }, defaults: { baseUrl: "https://gitlab.com/api/v4" }, hint: "PAT or project token — self-hosted instances need custom URL" },
  google:       { name: "Google (Drive/Sheets)",category: "Data",          icon: "FileText",  color: "#34d399", fields: { baseUrl: false, apiKey: false, token: false, credPath: true  }, defaults: { baseUrl: "" }, hint: "Path to service account credentials JSON file" },
  openrouter:   { name: "OpenRouter",          category: "Gateway",        icon: "Globe",     color: "#a78bfa", fields: { baseUrl: true, apiKey: true,  token: false, credPath: false }, defaults: { baseUrl: "https://openrouter.ai/api/v1" }, hint: "Multi-model gateway — drop-in OpenAI compatible" },
  getlate:      { name: "getlate.dev",         category: "Gateway",        icon: "Globe",     color: "#fbbf24", fields: { baseUrl: true, apiKey: true,  token: false, credPath: false }, defaults: { baseUrl: "https://api.getlate.dev/v1" }, hint: "API gateway with rate limiting and caching" },
  lmstudio:     { name: "LM Studio",           category: "LLM (Local)",    icon: "HardDrive", color: "#34d399", fields: { baseUrl: true, apiKey: false, token: false, credPath: false }, defaults: { baseUrl: "http://127.0.0.1:1234/v1" }, hint: "Local model server — OpenAI-compatible API" },
  custom:       { name: "Custom Service",      category: "Custom",         icon: "Settings",  color: "#8899aa", fields: { baseUrl: true, apiKey: true,  token: true,  credPath: true  }, defaults: { baseUrl: "" }, hint: "Configure any service — enable only the fields you need" },
};

const CATEGORY_ORDER = ["LLM", "LLM (Local)", "Media / Audio", "Media / Video", "Git / DevOps", "Data", "Gateway", "Custom"];

const ICON_MAP = { HardDrive, Cloud, Mic, Video, GitBranch, FileText, Globe, Settings, Server, Key };

// --- Simulated Data ---
const generateDailyData = () => {
  const data = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    data.push({
      date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      ollama: Math.floor(Math.random() * 80000 + 20000),
      openai: Math.floor(Math.random() * 45000 + 5000),
      anthropic: Math.floor(Math.random() * 35000 + 8000),
    });
  }
  return data;
};
const generateWeeklyData = () => {
  const data = [];
  for (let i = 11; i >= 0; i--) {
    data.push({
      date: `W${52 - i}`,
      ollama: Math.floor(Math.random() * 500000 + 150000),
      openai: Math.floor(Math.random() * 280000 + 40000),
      anthropic: Math.floor(Math.random() * 200000 + 60000),
    });
  }
  return data;
};
const generateMonthlyData = () =>
  ["Sep","Oct","Nov","Dec","Jan","Feb"].map((m) => ({
    date: m,
    ollama: Math.floor(Math.random() * 2000000 + 600000),
    openai: Math.floor(Math.random() * 1100000 + 200000),
    anthropic: Math.floor(Math.random() * 800000 + 250000),
  }));

const initialConnections = [
  { id: 1, name: "Ollama (Local)",  service: "ollama",     category: "LLM",            baseUrl: "http://127.0.0.1:11434",       apiKey: "",                    token: "", credPath: "", status: "healthy",  latency: 45,  lastSuccess: "2 min ago",  requests24h: 847, errors24h: 2, enabled: true },
  { id: 2, name: "OpenAI",          service: "openai",     category: "LLM",            baseUrl: "https://api.openai.com/v1",    apiKey: "sk-proj-a8Xf...d3Km", token: "", credPath: "", status: "healthy",  latency: 320, lastSuccess: "5 min ago",  requests24h: 234, errors24h: 0, enabled: true },
  { id: 3, name: "Anthropic",       service: "anthropic",  category: "LLM",            baseUrl: "https://api.anthropic.com/v1", apiKey: "sk-ant-...w9Pq",      token: "", credPath: "", status: "degraded", latency: 890, lastSuccess: "12 min ago", requests24h: 156, errors24h: 8, enabled: true },
  { id: 4, name: "ElevenLabs",      service: "elevenlabs", category: "Media / Audio",  baseUrl: "https://api.elevenlabs.io/v1", apiKey: "el-...k8Rm",          token: "", credPath: "", status: "healthy",  latency: 210, lastSuccess: "8 min ago",  requests24h: 42,  errors24h: 0, enabled: true },
  { id: 5, name: "GitHub",          service: "github",     category: "Git / DevOps",   baseUrl: "https://api.github.com",       apiKey: "",                    token: "ghp_...xN4p", credPath: "", status: "healthy",  latency: 180, lastSuccess: "1 hr ago",  requests24h: 18,  errors24h: 1, enabled: true },
  { id: 6, name: "Sora 2 Pro",      service: "sora",       category: "Media / Video",  baseUrl: "https://api.openai.com/v1",    apiKey: "sk-proj-a8Xf...d3Km", token: "", credPath: "", status: "healthy",  latency: 4200, lastSuccess: "22 min ago", requests24h: 6, errors24h: 0, enabled: false },
];

const initialCostConfig = [
  { model: "qwen2.5:32b-instruct", provider: "ollama", inputCost: 0, outputCost: 0 },
  { model: "llama3.2:1b", provider: "ollama", inputCost: 0, outputCost: 0 },
  { model: "gpt-4o-mini", provider: "openai", inputCost: 0.15, outputCost: 0.60 },
  { model: "gpt-4o", provider: "openai", inputCost: 2.50, outputCost: 10.00 },
  { model: "claude-sonnet-4-5", provider: "anthropic", inputCost: 3.00, outputCost: 15.00 },
  { model: "claude-haiku-4-5", provider: "anthropic", inputCost: 1.00, outputCost: 5.00 },
];

const recentRequests = [
  { id: 1, time: "14:32:07", model: "qwen2.5:32b-instruct", provider: "ollama",     promptTokens: 1240, completionTokens: 456, cost: 0,      latency: 38,   status: "success" },
  { id: 2, time: "14:31:52", model: "claude-sonnet-4-5",     provider: "anthropic",  promptTokens: 2100, completionTokens: 890, cost: 0.0197, latency: 1240, status: "success" },
  { id: 3, time: "14:31:18", model: "gpt-4o-mini",           provider: "openai",     promptTokens: 980,  completionTokens: 320, cost: 0.0003, latency: 450,  status: "success" },
  { id: 4, time: "14:31:05", model: "eleven_multilingual_v2", provider: "elevenlabs", promptTokens: 340,  completionTokens: 0,   cost: 0.003,  latency: 890,  status: "success" },
  { id: 5, time: "14:30:44", model: "claude-haiku-4-5",      provider: "anthropic",  promptTokens: 1560, completionTokens: 0,   cost: 0,      latency: 0,    status: "error" },
  { id: 6, time: "14:30:02", model: "qwen2.5:32b-instruct",  provider: "ollama",     promptTokens: 890,  completionTokens: 234, cost: 0,      latency: 29,   status: "success" },
  { id: 7, time: "14:29:31", model: "gpt-4o",                provider: "openai",     promptTokens: 3200, completionTokens: 1100,cost: 0.019,  latency: 2100, status: "success" },
  { id: 8, time: "14:28:55", model: "sora-2-pro",            provider: "openai",     promptTokens: 200,  completionTokens: 0,   cost: 0.40,   latency: 42000,status: "success" },
];

// --- Colors ---
const COLORS = {
  bg: "#0a0e17", surface: "#111827", surfaceAlt: "#1a2332",
  border: "#1e2d3d", borderLight: "#2a3a4d",
  text: "#e2e8f0", textMuted: "#8899aa", textDim: "#556677",
  accent: "#22d3ee", accentDim: "rgba(34,211,238,0.12)",
  green: "#34d399", greenDim: "rgba(52,211,153,0.12)",
  yellow: "#fbbf24", yellowDim: "rgba(251,191,36,0.12)",
  red: "#f87171", redDim: "rgba(248,113,113,0.12)",
  purple: "#a78bfa", purpleDim: "rgba(167,139,250,0.12)",
  pink: "#f472b6", orange: "#fb923c",
  ollama: "#34d399", openai: "#22d3ee", anthropic: "#a78bfa",
  elevenlabs: "#f472b6", github: "#e2e8f0", sora: "#fb923c",
  kie: "#38bdf8", openrouter: "#a78bfa", getlate: "#fbbf24",
  lmstudio: "#34d399", google: "#34d399", gitlab: "#fb923c", custom: "#8899aa",
};

// --- Shared Components ---
const StatusDot = ({ status }) => {
  const color = status === "healthy" ? COLORS.green : status === "degraded" ? COLORS.yellow : COLORS.red;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color, boxShadow: `0 0 8px ${color}60`, animation: status !== "healthy" ? "pulse 2s infinite" : undefined }} />
      <span style={{ color, fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{status}</span>
    </span>
  );
};

const ServiceBadge = ({ service }) => {
  const tpl = SERVICE_TEMPLATES[service] || SERVICE_TEMPLATES.custom;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 700, color: tpl.color, background: `${tpl.color}18`, padding: "2px 8px", borderRadius: 4, letterSpacing: "0.04em" }}>
      {tpl.category}
    </span>
  );
};

const Card = ({ children, style }) => (
  <div style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: 24, ...style }}>{children}</div>
);

const StatCard = ({ icon: Icon, label, value, sub, color = COLORS.accent }) => (
  <Card style={{ display: "flex", flexDirection: "column", gap: 8 }}>
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ width: 32, height: 32, borderRadius: 8, background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Icon size={16} color={color} />
      </div>
      <span style={{ fontSize: 12, color: COLORS.textMuted, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
    </div>
    <div style={{ fontSize: 28, fontWeight: 700, color: COLORS.text, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.02em" }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: COLORS.textDim }}>{sub}</div>}
  </Card>
);

const TabBar = ({ tabs, active, onChange }) => (
  <div style={{ display: "flex", gap: 2, background: COLORS.surfaceAlt, borderRadius: 8, padding: 3, width: "fit-content" }}>
    {tabs.map((t) => (
      <button key={t.key} onClick={() => onChange(t.key)} style={{
        padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600, letterSpacing: "0.03em",
        background: active === t.key ? COLORS.accent : "transparent", color: active === t.key ? COLORS.bg : COLORS.textMuted, transition: "all 0.2s",
      }}>{t.label}</button>
    ))}
  </div>
);

const Modal = ({ open, onClose, title, children, width = 520 }) => {
  if (!open) return null;
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center" }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 16, padding: 28, width, maxWidth: "92vw", maxHeight: "88vh", overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: COLORS.text }}>{title}</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: COLORS.textMuted, padding: 4 }}><X size={18} /></button>
        </div>
        {children}
      </div>
    </div>
  );
};

const Input = ({ label, value, onChange, type = "text", placeholder, mono, readOnly, hint }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
    <label style={{ fontSize: 12, fontWeight: 600, color: COLORS.textMuted, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</label>
    <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} readOnly={readOnly}
      style={{ background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: "10px 14px", color: COLORS.text, fontSize: 14, outline: "none", fontFamily: mono ? "'JetBrains Mono', monospace" : "inherit", opacity: readOnly ? 0.6 : 1 }} />
    {hint && <span style={{ fontSize: 11, color: COLORS.textDim, marginTop: -2 }}>{hint}</span>}
  </div>
);

const Btn = ({ children, onClick, variant = "primary", size = "md", disabled, style: s }) => {
  const base = { border: "none", borderRadius: 8, cursor: disabled ? "default" : "pointer", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 6, opacity: disabled ? 0.4 : 1, transition: "all 0.15s", padding: size === "sm" ? "6px 12px" : "10px 18px", fontSize: size === "sm" ? 12 : 14 };
  const v = { primary: { background: COLORS.accent, color: COLORS.bg }, danger: { background: COLORS.red, color: "#fff" }, ghost: { background: "transparent", color: COLORS.textMuted, border: `1px solid ${COLORS.border}` }, success: { background: COLORS.green, color: COLORS.bg } };
  return <button onClick={onClick} disabled={disabled} style={{ ...base, ...v[variant], ...s }}>{children}</button>;
};

const CredentialField = ({ label, value, placeholder, hint, icon: FieldIcon }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
    <label style={{ fontSize: 12, fontWeight: 600, color: COLORS.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: 6 }}>
      {FieldIcon && <FieldIcon size={12} />} {label}
    </label>
    <input type="password" defaultValue="" placeholder={placeholder}
      style={{ background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: "10px 14px", color: COLORS.text, fontSize: 14, outline: "none", fontFamily: "'JetBrains Mono', monospace" }} />
    {hint && <span style={{ fontSize: 11, color: COLORS.textDim }}>{hint}</span>}
  </div>
);

// --- Main ---
export default function OpenClawDashboard() {
  const [view, setView] = useState("overview");
  const [connections, setConnections] = useState(initialConnections);
  const [costConfig, setCostConfig] = useState(initialCostConfig);
  const [budgetLimit, setBudgetLimit] = useState({ daily: 5, weekly: 25, monthly: 80 });
  const [timeRange, setTimeRange] = useState("daily");
  const [authenticated, setAuthenticated] = useState(false);
  const [showKeyFor, setShowKeyFor] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [showCostEdit, setShowCostEdit] = useState(null);
  const [showBudgetEdit, setShowBudgetEdit] = useState(false);

  // Add provider flow
  const [showAddConn, setShowAddConn] = useState(false);
  const [addStep, setAddStep] = useState("pick"); // "pick" | "configure"
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [newConnName, setNewConnName] = useState("");
  const [newConnBaseUrl, setNewConnBaseUrl] = useState("");
  const [newConnApiKey, setNewConnApiKey] = useState("");
  const [newConnToken, setNewConnToken] = useState("");
  const [newConnCredPath, setNewConnCredPath] = useState("");
  const [customFieldToggles, setCustomFieldToggles] = useState({ baseUrl: true, apiKey: true, token: false, credPath: false });
  const [searchFilter, setSearchFilter] = useState("");

  // Edit provider
  const [editConn, setEditConn] = useState(null);

  const dailyData = generateDailyData();
  const weeklyData = generateWeeklyData();
  const monthlyData = generateMonthlyData();
  const chartData = timeRange === "daily" ? dailyData : timeRange === "weekly" ? weeklyData : monthlyData;

  const todayTotals = dailyData[dailyData.length - 1];
  const todayTotal = todayTotals.ollama + todayTotals.openai + todayTotals.anthropic;
  const totalRequests = connections.reduce((a, c) => a + c.requests24h, 0);
  const totalErrors = connections.reduce((a, c) => a + c.errors24h, 0);
  const estimatedDailyCost = recentRequests.filter((r) => r.status === "success").reduce((s, r) => s + r.cost, 0) * 12;
  const budgetPct = (estimatedDailyCost / budgetLimit.daily) * 100;

  const requireAuth = (fn) => { if (!authenticated) setAuthenticated(true); fn(); };

  const resetAddFlow = () => { setShowAddConn(false); setAddStep("pick"); setSelectedTemplate(null); setNewConnName(""); setNewConnBaseUrl(""); setNewConnApiKey(""); setNewConnToken(""); setNewConnCredPath(""); setSearchFilter(""); setCustomFieldToggles({ baseUrl: true, apiKey: true, token: false, credPath: false }); };

  const selectTemplate = (key) => {
    const tpl = SERVICE_TEMPLATES[key];
    setSelectedTemplate(key);
    setNewConnName(key === "custom" ? "" : tpl.name);
    setNewConnBaseUrl(tpl.defaults.baseUrl);
    setNewConnApiKey(""); setNewConnToken(""); setNewConnCredPath("");
    setAddStep("configure");
  };

  const handleAddConnection = () => {
    const tpl = SERVICE_TEMPLATES[selectedTemplate] || SERVICE_TEMPLATES.custom;
    const id = Math.max(...connections.map((c) => c.id), 0) + 1;
    const mask = (v, prefix = "") => v ? `${prefix}${v.slice(0, 4)}...${v.slice(-4)}` : "";
    setConnections([...connections, {
      id, name: newConnName || tpl.name, service: selectedTemplate, category: tpl.category,
      baseUrl: newConnBaseUrl || tpl.defaults.baseUrl,
      apiKey: mask(newConnApiKey), token: mask(newConnToken), credPath: newConnCredPath,
      status: "healthy", latency: 0, lastSuccess: "just now", requests24h: 0, errors24h: 0, enabled: true,
    }]);
    resetAddFlow();
  };

  const handleDeleteConnection = (id) => { setConnections(connections.filter((c) => c.id !== id)); setConfirmDelete(null); };
  const handleToggleConnection = (id) => { setConnections(connections.map((c) => c.id === id ? { ...c, enabled: !c.enabled } : c)); };

  // Group templates by category
  const grouped = {};
  Object.entries(SERVICE_TEMPLATES).forEach(([key, tpl]) => {
    if (!grouped[tpl.category]) grouped[tpl.category] = [];
    grouped[tpl.category].push({ key, ...tpl });
  });

  const filteredGrouped = {};
  const lowerFilter = searchFilter.toLowerCase();
  Object.entries(grouped).forEach(([cat, items]) => {
    const filtered = items.filter((i) => i.name.toLowerCase().includes(lowerFilter) || cat.toLowerCase().includes(lowerFilter) || i.key.toLowerCase().includes(lowerFilter));
    if (filtered.length > 0) filteredGrouped[cat] = filtered;
  });

  const pieData = [
    { name: "Ollama", value: connections.filter((c) => c.service === "ollama").reduce((s, c) => s + c.requests24h, 0), color: COLORS.ollama },
    { name: "OpenAI", value: connections.filter((c) => ["openai", "sora"].includes(c.service)).reduce((s, c) => s + c.requests24h, 0), color: COLORS.openai },
    { name: "Anthropic", value: connections.filter((c) => c.service === "anthropic").reduce((s, c) => s + c.requests24h, 0), color: COLORS.purple },
    { name: "Other", value: connections.filter((c) => !["ollama", "openai", "sora", "anthropic"].includes(c.service)).reduce((s, c) => s + c.requests24h, 0), color: COLORS.pink },
  ].filter((d) => d.value > 0);

  const navItems = [
    { key: "overview", icon: BarChart3, label: "Overview" },
    { key: "connections", icon: Server, label: "Connections" },
    { key: "costs", icon: DollarSign, label: "Costs" },
    { key: "activity", icon: List, label: "Activity" },
  ];

  const getConnIcon = (service) => {
    const tpl = SERVICE_TEMPLATES[service];
    if (!tpl) return Server;
    return ICON_MAP[tpl.icon] || Server;
  };
  const getConnColor = (service) => COLORS[service] || COLORS.accent;

  // Determine which credential fields a connection has
  const getCredSummary = (conn) => {
    const parts = [];
    if (conn.apiKey) parts.push({ label: "API Key", value: conn.apiKey, field: "apiKey" });
    if (conn.token) parts.push({ label: "Token / PAT", value: conn.token, field: "token" });
    if (conn.credPath) parts.push({ label: "Credentials", value: conn.credPath, field: "credPath" });
    if (parts.length === 0) parts.push({ label: "Auth", value: "None required", field: null });
    return parts;
  };

  return (
    <div style={{ minHeight: "100vh", background: COLORS.bg, color: COLORS.text, fontFamily: "'DM Sans', -apple-system, sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        @keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.4} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: ${COLORS.bg}; }
        ::-webkit-scrollbar-thumb { background: ${COLORS.border}; border-radius: 3px; }
        .nav-btn:hover { background: ${COLORS.surfaceAlt} !important; }
        .row-hover:hover { background: ${COLORS.surfaceAlt} !important; }
        .svc-card:hover { border-color: ${COLORS.accent} !important; background: ${COLORS.surfaceAlt} !important; transform: translateY(-1px); }
        .toggle-track { width:36px;height:20px;border-radius:10px;position:relative;cursor:pointer;transition:background 0.2s; }
        .toggle-thumb { width:16px;height:16px;border-radius:50%;background:#fff;position:absolute;top:2px;transition:left 0.2s; }
      `}</style>

      {/* Header */}
      <header style={{ borderBottom: `1px solid ${COLORS.border}`, padding: "14px 28px", display: "flex", alignItems: "center", justifyContent: "space-between", background: `${COLORS.surface}cc`, backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.purple})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 0 20px ${COLORS.accent}30` }}>
            <Shield size={18} color={COLORS.bg} strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.02em" }}>OpenClaw Hub</div>
            <div style={{ fontSize: 11, color: COLORS.textDim, fontFamily: "'JetBrains Mono', monospace" }}>127.0.0.1:8080</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: COLORS.green }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: COLORS.green, boxShadow: `0 0 6px ${COLORS.green}` }} />
            {connections.filter((c) => c.enabled).length} of {connections.length} active
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 12px", background: authenticated ? COLORS.greenDim : COLORS.surfaceAlt, borderRadius: 8, fontSize: 12, fontWeight: 600, color: authenticated ? COLORS.green : COLORS.textMuted, cursor: "pointer" }}
            onClick={() => setAuthenticated(!authenticated)}>
            <Lock size={12} /> {authenticated ? "Authenticated" : "Click to Auth"}
          </div>
        </div>
      </header>

      <div style={{ display: "flex", minHeight: "calc(100vh - 65px)" }}>
        {/* Sidebar */}
        <nav style={{ width: 200, borderRight: `1px solid ${COLORS.border}`, padding: "16px 10px", display: "flex", flexDirection: "column", gap: 4, background: COLORS.surface }}>
          {navItems.map((item) => (
            <button key={item.key} className="nav-btn" onClick={() => setView(item.key)} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderRadius: 8, border: "none",
              background: view === item.key ? COLORS.accentDim : "transparent", color: view === item.key ? COLORS.accent : COLORS.textMuted,
              cursor: "pointer", fontSize: 13, fontWeight: 600, transition: "all 0.15s", textAlign: "left",
            }}>
              <item.icon size={16} /> {item.label}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <div style={{ padding: "12px 14px", borderTop: `1px solid ${COLORS.border}`, marginTop: 8 }}>
            <div style={{ fontSize: 11, color: COLORS.textDim, fontFamily: "'JetBrains Mono', monospace" }}>v1.0.0</div>
            <div style={{ fontSize: 11, color: COLORS.textDim }}>Apache 2.0</div>
          </div>
        </nav>

        {/* Main Content */}
        <main style={{ flex: 1, padding: 28, overflowY: "auto", maxHeight: "calc(100vh - 65px)" }}>

          {/* ==================== OVERVIEW ==================== */}
          {view === "overview" && (
            <div style={{ animation: "fadeIn 0.3s ease-out" }}>
              <h2 style={{ margin: "0 0 24px", fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em" }}>Dashboard Overview</h2>
              {budgetPct > 70 && (
                <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 18px", background: budgetPct > 90 ? COLORS.redDim : COLORS.yellowDim, border: `1px solid ${budgetPct > 90 ? COLORS.red : COLORS.yellow}40`, borderRadius: 10, marginBottom: 20 }}>
                  <AlertTriangle size={16} color={budgetPct > 90 ? COLORS.red : COLORS.yellow} />
                  <span style={{ fontSize: 13, color: budgetPct > 90 ? COLORS.red : COLORS.yellow, fontWeight: 600 }}>
                    Daily budget {Math.round(budgetPct)}% used — ${estimatedDailyCost.toFixed(2)} of ${budgetLimit.daily.toFixed(2)} limit
                  </span>
                </div>
              )}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
                <StatCard icon={Zap} label="Tokens Today" value={todayTotal.toLocaleString()} sub="Across all providers" color={COLORS.accent} />
                <StatCard icon={Activity} label="Requests (24h)" value={totalRequests.toLocaleString()} sub={`${totalErrors} errors`} color={COLORS.green} />
                <StatCard icon={DollarSign} label="Est. Daily Cost" value={`$${estimatedDailyCost.toFixed(2)}`} sub={`Budget: $${budgetLimit.daily}`} color={COLORS.yellow} />
                <StatCard icon={Server} label="Connections" value={connections.filter((c) => c.enabled).length} sub={`${connections.length} configured`} color={COLORS.purple} />
              </div>
              <Card style={{ marginBottom: 28 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Token Usage</h3>
                  <TabBar tabs={[{ key: "daily", label: "Day" }, { key: "weekly", label: "Week" }, { key: "monthly", label: "Month" }]} active={timeRange} onChange={setTimeRange} />
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chartData} barGap={2}>
                    <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                    <XAxis dataKey="date" tick={{ fill: COLORS.textDim, fontSize: 11 }} axisLine={{ stroke: COLORS.border }} tickLine={false} />
                    <YAxis tick={{ fill: COLORS.textDim, fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}k` : v} />
                    <Tooltip contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 8, fontSize: 12 }} labelStyle={{ color: COLORS.text, fontWeight: 600 }} formatter={(v, name) => [v.toLocaleString() + " tokens", name.charAt(0).toUpperCase() + name.slice(1)]} />
                    <Legend wrapperStyle={{ fontSize: 12, color: COLORS.textMuted }} />
                    <Bar dataKey="ollama" stackId="a" fill={COLORS.ollama} />
                    <Bar dataKey="openai" stackId="a" fill={COLORS.openai} />
                    <Bar dataKey="anthropic" stackId="a" fill={COLORS.purple} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <Card>
                  <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700 }}>Request Distribution (24h)</h3>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart><Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                      {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                    </Pie><Tooltip contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 8, fontSize: 12 }} /></PieChart>
                  </ResponsiveContainer>
                  <div style={{ display: "flex", justifyContent: "center", gap: 20, marginTop: 8 }}>
                    {pieData.map((p) => <div key={p.name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: COLORS.textMuted }}><span style={{ width: 8, height: 8, borderRadius: 2, background: p.color }} />{p.name}: {p.value}</div>)}
                  </div>
                </Card>
                <Card>
                  <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700 }}>Connection Health</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {connections.map((conn) => {
                      const ConnIcon = getConnIcon(conn.service);
                      return (
                        <div key={conn.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", background: COLORS.surfaceAlt, borderRadius: 8, opacity: conn.enabled ? 1 : 0.4 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <ConnIcon size={14} color={getConnColor(conn.service)} />
                            <span style={{ fontSize: 13, fontWeight: 600 }}>{conn.name}</span>
                            <StatusDot status={conn.enabled ? conn.status : "offline"} />
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 12, color: COLORS.textDim }}>
                            <span>{conn.latency > 10000 ? `${(conn.latency/1000).toFixed(1)}s` : `${conn.latency}ms`}</span>
                            <span>{conn.requests24h} req</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* ==================== CONNECTIONS ==================== */}
          {view === "connections" && (
            <div style={{ animation: "fadeIn 0.3s ease-out" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Connections</h2>
                <Btn onClick={() => requireAuth(() => { resetAddFlow(); setShowAddConn(true); })}><Plus size={14} /> Add Connection</Btn>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {connections.map((conn) => {
                  const ConnIcon = getConnIcon(conn.service);
                  const creds = getCredSummary(conn);
                  return (
                    <Card key={conn.id} style={{ opacity: conn.enabled ? 1 : 0.5, borderColor: conn.enabled ? (conn.status === "degraded" ? `${COLORS.yellow}40` : COLORS.border) : COLORS.border }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                          <div style={{ width: 44, height: 44, borderRadius: 10, background: `${getConnColor(conn.service)}15`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <ConnIcon size={20} color={getConnColor(conn.service)} />
                          </div>
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                              <span style={{ fontSize: 16, fontWeight: 700 }}>{conn.name}</span>
                              <ServiceBadge service={conn.service} />
                              <StatusDot status={conn.enabled ? conn.status : "offline"} />
                            </div>
                            <div style={{ fontSize: 12, color: COLORS.textDim, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>{conn.baseUrl || "—"}</div>
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                          <Btn variant="ghost" size="sm" onClick={() => handleToggleConnection(conn.id)}>{conn.enabled ? "Disable" : "Enable"}</Btn>
                          <Btn variant="ghost" size="sm" onClick={() => requireAuth(() => setEditConn({ ...conn }))}><Edit3 size={12} /> Edit</Btn>
                          <Btn variant="ghost" size="sm" onClick={() => setConfirmDelete(conn.id)} style={{ color: COLORS.red, borderColor: `${COLORS.red}40` }}><Trash2 size={12} /></Btn>
                        </div>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: `repeat(${3 + creds.length}, 1fr)`, gap: 16, marginTop: 20, paddingTop: 16, borderTop: `1px solid ${COLORS.border}` }}>
                        <div>
                          <div style={{ fontSize: 11, color: COLORS.textDim, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Latency</div>
                          <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: conn.latency > 2000 ? COLORS.yellow : COLORS.text }}>
                            {conn.latency > 10000 ? `${(conn.latency/1000).toFixed(1)}s` : `${conn.latency}ms`}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 11, color: COLORS.textDim, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Requests (24h)</div>
                          <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{conn.requests24h}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 11, color: COLORS.textDim, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Errors (24h)</div>
                          <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: conn.errors24h > 0 ? COLORS.red : COLORS.green }}>{conn.errors24h}</div>
                        </div>
                        {creds.map((cred, ci) => (
                          <div key={ci}>
                            <div style={{ fontSize: 11, color: COLORS.textDim, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{cred.label}</div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 13, fontFamily: "'JetBrains Mono', monospace", color: cred.field ? COLORS.textMuted : COLORS.green }}>
                                {cred.field ? (showKeyFor === `${conn.id}-${cred.field}` ? "sk-proj-a8XfK2mNq7...d3Km4pQrZ8" : cred.value) : cred.value}
                              </span>
                              {cred.field && cred.field !== "credPath" && (
                                <button onClick={() => requireAuth(() => setShowKeyFor(showKeyFor === `${conn.id}-${cred.field}` ? null : `${conn.id}-${cred.field}`))}
                                  style={{ background: "none", border: "none", cursor: "pointer", color: COLORS.textDim, padding: 2 }}>
                                  {showKeyFor === `${conn.id}-${cred.field}` ? <EyeOff size={12} /> : <Eye size={12} />}
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      {confirmDelete === conn.id && (
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 16, padding: "12px 16px", background: COLORS.redDim, border: `1px solid ${COLORS.red}30`, borderRadius: 8 }}>
                          <span style={{ fontSize: 13, color: COLORS.red, fontWeight: 600 }}>Remove {conn.name}? This cannot be undone.</span>
                          <div style={{ display: "flex", gap: 8 }}>
                            <Btn variant="ghost" size="sm" onClick={() => setConfirmDelete(null)}>Cancel</Btn>
                            <Btn variant="danger" size="sm" onClick={() => handleDeleteConnection(conn.id)}><Trash2 size={12} /> Remove</Btn>
                          </div>
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {/* ==================== COSTS ==================== */}
          {view === "costs" && (
            <div style={{ animation: "fadeIn 0.3s ease-out" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Cost Configuration</h2>
                <Btn variant="ghost" onClick={() => setShowBudgetEdit(true)}><Settings size={14} /> Budget Limits</Btn>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 28 }}>
                {[
                  { label: "Daily", limit: budgetLimit.daily, spent: estimatedDailyCost },
                  { label: "Weekly", limit: budgetLimit.weekly, spent: estimatedDailyCost * 5.2 },
                  { label: "Monthly", limit: budgetLimit.monthly, spent: estimatedDailyCost * 22 },
                ].map((b) => {
                  const pct = Math.min((b.spent / b.limit) * 100, 100);
                  const color = pct > 90 ? COLORS.red : pct > 70 ? COLORS.yellow : COLORS.green;
                  return (
                    <Card key={b.label}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: COLORS.textMuted }}>{b.label} Budget</span>
                        <span style={{ fontSize: 12, color, fontWeight: 700 }}>{Math.round(pct)}%</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 12 }}>
                        <span style={{ fontSize: 24, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>${b.spent.toFixed(2)}</span>
                        <span style={{ fontSize: 13, color: COLORS.textDim }}>/ ${b.limit.toFixed(2)}</span>
                      </div>
                      <div style={{ height: 6, background: COLORS.surfaceAlt, borderRadius: 3 }}>
                        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 3, transition: "width 0.5s" }} />
                      </div>
                    </Card>
                  );
                })}
              </div>
              <Card>
                <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700 }}>Cost Per Token (per 1M tokens)</h3>
                <div style={{ borderRadius: 8, overflow: "hidden", border: `1px solid ${COLORS.border}` }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead><tr style={{ background: COLORS.surfaceAlt }}>
                      {["Model", "Provider", "Input Cost", "Output Cost", "Actions"].map((h) => (
                        <th key={h} style={{ padding: "10px 16px", textAlign: h === "Model" ? "left" : "right", fontWeight: 600, color: COLORS.textMuted, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                      ))}
                    </tr></thead>
                    <tbody>
                      {costConfig.map((c, i) => (
                        <tr key={i} className="row-hover" style={{ borderTop: `1px solid ${COLORS.border}` }}>
                          <td style={{ padding: "12px 16px", fontFamily: "'JetBrains Mono', monospace", fontWeight: 500, textAlign: "left" }}>{c.model}</td>
                          <td style={{ padding: "12px 16px", textAlign: "right" }}><ServiceBadge service={c.provider} /></td>
                          <td style={{ padding: "12px 16px", textAlign: "right", fontFamily: "'JetBrains Mono', monospace", color: c.inputCost === 0 ? COLORS.green : COLORS.text }}>{c.inputCost === 0 ? "FREE" : `$${c.inputCost.toFixed(2)}`}</td>
                          <td style={{ padding: "12px 16px", textAlign: "right", fontFamily: "'JetBrains Mono', monospace", color: c.outputCost === 0 ? COLORS.green : COLORS.text }}>{c.outputCost === 0 ? "FREE" : `$${c.outputCost.toFixed(2)}`}</td>
                          <td style={{ padding: "12px 16px", textAlign: "right" }}><Btn variant="ghost" size="sm" onClick={() => setShowCostEdit(i)}><Edit3 size={12} /> Edit</Btn></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              <Card style={{ marginTop: 20 }}>
                <h3 style={{ margin: "0 0 16px", fontSize: 15, fontWeight: 700 }}>Estimated Cost Over Time</h3>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={dailyData.map((d) => ({ date: d.date, cost: ((d.openai * 0.15 + d.anthropic * 3.0) / 1e6).toFixed(3) }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke={COLORS.border} />
                    <XAxis dataKey="date" tick={{ fill: COLORS.textDim, fontSize: 11 }} axisLine={{ stroke: COLORS.border }} tickLine={false} />
                    <YAxis tick={{ fill: COLORS.textDim, fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} />
                    <Tooltip contentStyle={{ background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 8, fontSize: 12 }} formatter={(v) => [`$${v}`, "Est. Cost"]} />
                    <Line type="monotone" dataKey="cost" stroke={COLORS.yellow} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </div>
          )}

          {/* ==================== ACTIVITY ==================== */}
          {view === "activity" && (
            <div style={{ animation: "fadeIn 0.3s ease-out" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Recent Activity</h2>
                <Btn variant="ghost"><RefreshCw size={14} /> Refresh</Btn>
              </div>
              <Card style={{ padding: 0, overflow: "hidden" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead><tr style={{ background: COLORS.surfaceAlt }}>
                    {["Time", "Model", "Service", "Prompt", "Completion", "Cost", "Latency", "Status"].map((h) => (
                      <th key={h} style={{ padding: "10px 16px", textAlign: h === "Time" || h === "Model" ? "left" : "right", fontWeight: 600, color: COLORS.textMuted, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {recentRequests.map((r) => (
                      <tr key={r.id} className="row-hover" style={{ borderTop: `1px solid ${COLORS.border}` }}>
                        <td style={{ padding: "12px 16px", fontFamily: "'JetBrains Mono', monospace", color: COLORS.textDim }}>{r.time}</td>
                        <td style={{ padding: "12px 16px", fontFamily: "'JetBrains Mono', monospace", fontWeight: 500 }}>{r.model}</td>
                        <td style={{ padding: "12px 16px", textAlign: "right" }}><ServiceBadge service={r.provider} /></td>
                        <td style={{ padding: "12px 16px", textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{r.promptTokens.toLocaleString()}</td>
                        <td style={{ padding: "12px 16px", textAlign: "right", fontFamily: "'JetBrains Mono', monospace" }}>{r.completionTokens.toLocaleString()}</td>
                        <td style={{ padding: "12px 16px", textAlign: "right", fontFamily: "'JetBrains Mono', monospace", color: r.cost === 0 ? COLORS.green : COLORS.yellow }}>{r.cost === 0 ? "FREE" : `$${r.cost.toFixed(4)}`}</td>
                        <td style={{ padding: "12px 16px", textAlign: "right", fontFamily: "'JetBrains Mono', monospace", color: r.latency > 2000 ? COLORS.yellow : COLORS.textMuted }}>{r.status === "error" ? "—" : r.latency > 10000 ? `${(r.latency/1000).toFixed(1)}s` : `${r.latency}ms`}</td>
                        <td style={{ padding: "12px 16px", textAlign: "right" }}>
                          {r.status === "success"
                            ? <span style={{ color: COLORS.green, display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600 }}><Check size={12} /> OK</span>
                            : <span style={{ color: COLORS.red, display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600 }}><X size={12} /> ERR</span>
                          }
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}
        </main>
      </div>

      {/* ==================== ADD CONNECTION MODAL ==================== */}
      <Modal open={showAddConn} onClose={resetAddFlow} title={addStep === "pick" ? "Add Connection" : `Configure ${SERVICE_TEMPLATES[selectedTemplate]?.name || "Connection"}`} width={addStep === "pick" ? 640 : 520}>
        {addStep === "pick" && (
          <div>
            {/* Search */}
            <div style={{ position: "relative", marginBottom: 20 }}>
              <Search size={16} style={{ position: "absolute", left: 12, top: 11, color: COLORS.textDim }} />
              <input value={searchFilter} onChange={(e) => setSearchFilter(e.target.value)} placeholder="Search services..."
                style={{ width: "100%", background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: "10px 14px 10px 38px", color: COLORS.text, fontSize: 14, outline: "none" }} />
            </div>
            {/* Grouped grid */}
            <div style={{ display: "flex", flexDirection: "column", gap: 20, maxHeight: "55vh", overflowY: "auto", paddingRight: 4 }}>
              {CATEGORY_ORDER.filter((cat) => filteredGrouped[cat]).map((cat) => (
                <div key={cat}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10, paddingLeft: 2 }}>{cat}</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    {filteredGrouped[cat].map((svc) => {
                      const SvcIcon = ICON_MAP[svc.icon] || Server;
                      return (
                        <div key={svc.key} className="svc-card" onClick={() => selectTemplate(svc.key)} style={{
                          display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
                          background: COLORS.surface, border: `1px solid ${COLORS.border}`, borderRadius: 10,
                          cursor: "pointer", transition: "all 0.15s",
                        }}>
                          <div style={{ width: 36, height: 36, borderRadius: 8, background: `${svc.color}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                            <SvcIcon size={16} color={svc.color} />
                          </div>
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.text }}>{svc.name}</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                              {svc.key === "custom" ? "Any service — full control" : svc.hint.split("—")[0].trim()}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {addStep === "configure" && selectedTemplate && (() => {
          const tpl = SERVICE_TEMPLATES[selectedTemplate];
          const isCustom = selectedTemplate === "custom";
          const showField = (f) => isCustom ? customFieldToggles[f] : tpl.fields[f];
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Service badge */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", background: `${tpl.color}10`, border: `1px solid ${tpl.color}25`, borderRadius: 10 }}>
                {(() => { const I = ICON_MAP[tpl.icon] || Server; return <I size={16} color={tpl.color} />; })()}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: tpl.color }}>{tpl.name}</div>
                  <div style={{ fontSize: 11, color: COLORS.textDim }}>{tpl.hint}</div>
                </div>
              </div>

              <Input label="Connection Name" value={newConnName} onChange={setNewConnName} placeholder="e.g. Production ElevenLabs" />

              {/* Custom field toggles */}
              {isCustom && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: COLORS.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Credential Fields Needed</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {[
                      { key: "baseUrl", label: "Base URL" },
                      { key: "apiKey", label: "API Key" },
                      { key: "token", label: "Token / PAT" },
                      { key: "credPath", label: "Credentials File" },
                    ].map((f) => (
                      <button key={f.key} onClick={() => setCustomFieldToggles({ ...customFieldToggles, [f.key]: !customFieldToggles[f.key] })}
                        style={{
                          padding: "6px 14px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer",
                          border: `1px solid ${customFieldToggles[f.key] ? COLORS.accent : COLORS.border}`,
                          background: customFieldToggles[f.key] ? COLORS.accentDim : "transparent",
                          color: customFieldToggles[f.key] ? COLORS.accent : COLORS.textMuted,
                          transition: "all 0.15s",
                        }}>
                        {customFieldToggles[f.key] ? <Check size={10} style={{ marginRight: 4, display: "inline" }} /> : null}
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Dynamic fields */}
              {showField("baseUrl") && (
                <Input label="Base URL" value={newConnBaseUrl} onChange={setNewConnBaseUrl} placeholder={tpl.defaults.baseUrl || "https://api.example.com/v1"} mono
                  hint={isCustom ? "The API endpoint URL" : undefined} />
              )}
              {showField("apiKey") && (
                <Input label="API Key" value={newConnApiKey} onChange={setNewConnApiKey} type="password" placeholder="sk-..." mono
                  hint="Your API key — stored locally, never transmitted except to this provider" />
              )}
              {showField("token") && (
                <Input label="Token / Personal Access Token" value={newConnToken} onChange={setNewConnToken} type="password" placeholder={selectedTemplate === "github" ? "ghp_..." : selectedTemplate === "gitlab" ? "glpat-..." : "token..."} mono
                  hint={selectedTemplate === "github" ? "GitHub PAT with repo + workflow scopes" : selectedTemplate === "gitlab" ? "GitLab PAT or project token" : "Access token for authentication"} />
              )}
              {showField("credPath") && (
                <Input label="Credentials File Path" value={newConnCredPath} onChange={setNewConnCredPath} placeholder="/path/to/credentials.json" mono
                  hint="Absolute path to the credentials file on the Hub host" />
              )}

              {/* Validation test note */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", background: COLORS.accentDim, borderRadius: 8, fontSize: 12, color: COLORS.accent }}>
                <RefreshCw size={13} />
                Hub will validate this connection with a test request before saving.
              </div>

              <div style={{ display: "flex", gap: 10, justifyContent: "space-between", marginTop: 8 }}>
                <Btn variant="ghost" onClick={() => setAddStep("pick")}>← Back</Btn>
                <div style={{ display: "flex", gap: 10 }}>
                  <Btn variant="ghost" onClick={resetAddFlow}>Cancel</Btn>
                  <Btn onClick={handleAddConnection} disabled={!newConnName}><Check size={14} /> Add Connection</Btn>
                </div>
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* ==================== EDIT CONNECTION MODAL ==================== */}
      <Modal open={!!editConn} onClose={() => setEditConn(null)} title={`Edit ${editConn?.name || ""}`}>
        {editConn && (() => {
          const tpl = SERVICE_TEMPLATES[editConn.service] || SERVICE_TEMPLATES.custom;
          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: `${tpl.color}10`, border: `1px solid ${tpl.color}25`, borderRadius: 10 }}>
                {(() => { const I = ICON_MAP[tpl.icon] || Server; return <I size={14} color={tpl.color} />; })()}
                <span style={{ fontSize: 12, fontWeight: 700, color: tpl.color }}>{tpl.category}</span>
              </div>
              <Input label="Connection Name" value={editConn.name} onChange={(v) => setEditConn({ ...editConn, name: v })} />
              {tpl.fields.baseUrl && <Input label="Base URL" value={editConn.baseUrl} onChange={(v) => setEditConn({ ...editConn, baseUrl: v })} mono />}
              {tpl.fields.apiKey && <CredentialField label="Update API Key" placeholder="Enter new key to replace current (leave blank to keep)" hint={editConn.apiKey ? `Current: ${editConn.apiKey}` : "No key currently set"} icon={Key} />}
              {tpl.fields.token && <CredentialField label="Update Token / PAT" placeholder="Enter new token to replace current (leave blank to keep)" hint={editConn.token ? `Current: ${editConn.token}` : "No token currently set"} icon={Key} />}
              {tpl.fields.credPath && <Input label="Credentials File Path" value={editConn.credPath || ""} onChange={(v) => setEditConn({ ...editConn, credPath: v })} placeholder="/path/to/credentials.json" mono />}
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", background: COLORS.yellowDim, borderRadius: 8, fontSize: 12, color: COLORS.yellow }}>
                <AlertTriangle size={14} />
                Changing credentials will trigger a connection validation test.
              </div>
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
                <Btn variant="ghost" onClick={() => setEditConn(null)}>Cancel</Btn>
                <Btn onClick={() => { setConnections(connections.map((c) => c.id === editConn.id ? { ...c, name: editConn.name, baseUrl: editConn.baseUrl, credPath: editConn.credPath } : c)); setEditConn(null); }}><Check size={14} /> Save Changes</Btn>
              </div>
            </div>
          );
        })()}
      </Modal>

      {/* ==================== EDIT COST MODAL ==================== */}
      <Modal open={showCostEdit !== null} onClose={() => setShowCostEdit(null)} title="Edit Cost Configuration">
        {showCostEdit !== null && costConfig[showCostEdit] && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Input label="Model" value={costConfig[showCostEdit].model} readOnly mono />
            <Input label="Input Cost (per 1M tokens)" value={costConfig[showCostEdit].inputCost} onChange={(v) => { const u = [...costConfig]; u[showCostEdit] = { ...u[showCostEdit], inputCost: parseFloat(v) || 0 }; setCostConfig(u); }} type="number" mono />
            <Input label="Output Cost (per 1M tokens)" value={costConfig[showCostEdit].outputCost} onChange={(v) => { const u = [...costConfig]; u[showCostEdit] = { ...u[showCostEdit], outputCost: parseFloat(v) || 0 }; setCostConfig(u); }} type="number" mono />
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <Btn variant="ghost" onClick={() => setShowCostEdit(null)}>Cancel</Btn>
              <Btn onClick={() => setShowCostEdit(null)}><Check size={14} /> Save</Btn>
            </div>
          </div>
        )}
      </Modal>

      {/* ==================== BUDGET MODAL ==================== */}
      <Modal open={showBudgetEdit} onClose={() => setShowBudgetEdit(false)} title="Budget Limits">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Input label="Daily Budget (USD)" value={budgetLimit.daily} onChange={(v) => setBudgetLimit({ ...budgetLimit, daily: parseFloat(v) || 0 })} type="number" mono />
          <Input label="Weekly Budget (USD)" value={budgetLimit.weekly} onChange={(v) => setBudgetLimit({ ...budgetLimit, weekly: parseFloat(v) || 0 })} type="number" mono />
          <Input label="Monthly Budget (USD)" value={budgetLimit.monthly} onChange={(v) => setBudgetLimit({ ...budgetLimit, monthly: parseFloat(v) || 0 })} type="number" mono />
          <div style={{ padding: "10px 14px", background: COLORS.accentDim, borderRadius: 8, fontSize: 12, color: COLORS.accent }}>
            Budget alerts appear on the dashboard when usage exceeds 70% of any limit.
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
            <Btn variant="ghost" onClick={() => setShowBudgetEdit(false)}>Cancel</Btn>
            <Btn onClick={() => setShowBudgetEdit(false)}><Check size={14} /> Save Limits</Btn>
          </div>
        </div>
      </Modal>
    </div>
  );
}
