# Schema/Code Mismatch Audit Report

**Date:** 2026-01-31
**Scope:** Database schema vs Analysis API vs Frontend types

---

## Summary

**Critical Issues Found:** 5
**Status:** All issues identified and ready for fix

### Root Cause
The analysis API (`packages/analysis/agenttrace_analysis/api.py`) queries columns that don't exist in the database schema, causing 500 errors when the web UI attempts to fetch data.

---

## Database Schema (Source of Truth)

### `traces` table
```sql
- trace_id (UUID, PK)
- name (TEXT)
- start_time (TIMESTAMPTZ)
- end_time (TIMESTAMPTZ)
- status (TEXT)
- metadata (JSONB)
- total_tokens (INTEGER)
- total_cost_usd (DECIMAL)
- total_latency_ms (INTEGER)
- agent_count (INTEGER)
- created_at (TIMESTAMPTZ)
```

**NOT IN SCHEMA:**
- ❌ `session_id` - DOES NOT EXIST
- ❌ `user_id` - DOES NOT EXIST

### `spans` table
```sql
- span_id (UUID, PK)
- trace_id (UUID, FK)
- parent_span_id (UUID, FK)
- agent_id (UUID, FK)
- name (TEXT)
- kind (TEXT)
- start_time (TIMESTAMPTZ)
- end_time (TIMESTAMPTZ)
- status (TEXT)
- model (TEXT)
- input_tokens (INTEGER)
- output_tokens (INTEGER)
- cost_usd (DECIMAL)
- input (JSONB)
- output (JSONB)
- error (JSONB)          ← NOTE: "error", not "error_message"
- attributes (JSONB)
- created_at (TIMESTAMPTZ)
```

**NOT IN SCHEMA:**
- ❌ `error_message` - should be `error` (JSONB)

---

## Issues Found

### Issue 1: `list_traces()` - Missing/Wrong Columns ❌

**Location:** `api.py:79`

**Current Query:**
```sql
SELECT trace_id, session_id, user_id, status, start_time, end_time, metadata
FROM traces
```

**Problems:**
- ❌ `session_id` - column does not exist
- ❌ `user_id` - column does not exist
- ❌ Missing `name` - required by frontend
- ❌ Missing `total_tokens` - required by frontend
- ❌ Missing `total_cost_usd` - required by frontend
- ❌ Missing `agent_count` - required by frontend
- ❌ Missing `span_count` - required by frontend (needs subquery)

**Frontend Expects (types.ts:9-20):**
```typescript
interface Trace {
  trace_id: string;
  name: string;
  status: TraceStatus;
  start_time: string;
  end_time?: string;
  agent_count: number;
  span_count: number;
  total_tokens: number;
  total_cost_usd: number;
  metadata?: Record<string, any>;
}
```

**Fix Required:**
```sql
SELECT
    t.trace_id,
    t.name,
    t.status,
    t.start_time,
    t.end_time,
    t.metadata,
    t.total_tokens,
    t.total_cost_usd,
    t.agent_count,
    (SELECT COUNT(*) FROM spans WHERE trace_id = t.trace_id) as span_count
FROM traces t
```

---

### Issue 2: `get_trace()` - Missing/Wrong Columns ❌

**Location:** `api.py:148-156`

**Current Code:**
```python
result = {
    "trace_id": trace["trace_id"],
    "session_id": trace["session_id"],      # ❌ Does not exist
    "user_id": trace["user_id"],            # ❌ Does not exist
    "status": trace["status"],
    "start_time": ...,
    "end_time": ...,
    "metadata": trace["metadata"],
    "span_count": counts["span_count"],
    "agent_count": counts["agent_count"],
}
```

**Problems:**
- ❌ `session_id` - column does not exist
- ❌ `user_id` - column does not exist
- ❌ Missing `name` - required by frontend
- ❌ Missing `total_tokens` - required by frontend
- ❌ Missing `total_cost_usd` - required by frontend

**Fix Required:**
```python
result = {
    "trace_id": trace["trace_id"],
    "name": trace["name"],
    "status": trace["status"],
    "start_time": ...,
    "end_time": ...,
    "metadata": trace["metadata"],
    "total_tokens": trace["total_tokens"],
    "total_cost_usd": float(trace["total_cost_usd"]) if trace["total_cost_usd"] else 0,
    "span_count": counts["span_count"],
    "agent_count": counts["agent_count"],
}
```

---

### Issue 3: `classify_trace_failures()` - Wrong Column Name ❌

**Location:** `api.py:312`

**Current Query:**
```sql
SELECT
    span_id, parent_span_id, agent_id, name, kind, status,
    start_time, end_time, input, output, error_message,     # ❌ Wrong
    attributes, input_tokens, output_tokens, cost_usd
FROM spans
```

**Problem:**
- ❌ `error_message` should be `error` (JSONB column)

**Fix Required:**
```sql
SELECT
    span_id, parent_span_id, agent_id, name, kind, status,
    start_time, end_time, input, output, error,
    attributes, input_tokens, output_tokens, cost_usd, model
FROM spans
```

---

### Issue 4: `list_trace_spans()` - Wrong Column Name ❌

**Location:** `api.py:409, 433`

**Current Query:**
```sql
SELECT
    span_id, parent_span_id, agent_id, name, kind, status,
    start_time, end_time, input, output, error_message,     # ❌ Wrong
    attributes, input_tokens, output_tokens, cost_usd
FROM spans
```

**Current Response:**
```python
"error_message": span["error_message"],  # ❌ Wrong
```

**Problems:**
- ❌ `error_message` should be `error` (JSONB column)
- ❌ Missing `model` field
- ❌ Missing `trace_id` in response

**Fix Required:**
```sql
SELECT
    span_id, trace_id, parent_span_id, agent_id, name, kind, status,
    start_time, end_time, model, input, output, error,
    attributes, input_tokens, output_tokens, cost_usd
FROM spans
```

```python
"error": span["error"],
"model": span["model"],
"trace_id": trace_id,
```

---

### Issue 5: `get_span()` - Wrong Column Name ❌

**Location:** `api.py:470, 504`

**Current Query:**
```sql
SELECT
    s.span_id, s.trace_id, s.parent_span_id, s.agent_id,
    s.name, s.kind, s.status, s.start_time, s.end_time,
    s.input, s.output, s.error_message, s.attributes,     # ❌ Wrong
    s.input_tokens, s.output_tokens, s.cost_usd,
    a.name as agent_name, a.role as agent_role
FROM spans s
```

**Current Response:**
```python
"error_message": span["error_message"],  # ❌ Wrong
```

**Problem:**
- ❌ `error_message` should be `error` (JSONB column)

**Fix Required:**
```sql
SELECT
    s.span_id, s.trace_id, s.parent_span_id, s.agent_id,
    s.name, s.kind, s.status, s.start_time, s.end_time,
    s.model, s.input, s.output, s.error, s.attributes,
    s.input_tokens, s.output_tokens, s.cost_usd,
    a.name as agent_name, a.role as agent_role
FROM spans s
```

```python
"error": span["error"],
"model": span["model"],
```

---

## Frontend Type Compatibility

### ✅ Properly Aligned After Fixes

**Trace interface** will match:
- ✓ All required fields present
- ✓ No extra fields that don't exist in schema
- ✓ `span_count` computed via subquery

**Span interface** will match:
- ✓ `error` as JSONB (not `error_message`)
- ✓ `model` field included
- ✓ All required fields present

---

## Action Plan

1. ✅ **Remove all references to `session_id` and `user_id`** - these columns never existed
2. ✅ **Fix `list_traces()` query** - include name, total_tokens, total_cost_usd, agent_count, span_count
3. ✅ **Fix `get_trace()` response** - include name, total_tokens, total_cost_usd
4. ✅ **Replace `error_message` with `error`** in all span queries
5. ✅ **Add `model` field** to span responses where missing

---

## Testing Checklist

After fixes applied:

- [ ] `GET /api/traces` returns 200 (not 500)
- [ ] Response includes: name, total_tokens, total_cost_usd, agent_count, span_count
- [ ] No `session_id` or `user_id` in response
- [ ] `GET /api/traces/{trace_id}` returns all required fields
- [ ] `GET /api/traces/{trace_id}/spans` uses `error` (not `error_message`)
- [ ] `GET /api/spans/{span_id}` uses `error` (not `error_message`)
- [ ] Frontend loads without console errors
- [ ] All unit tests still pass

---

## Notes

- The schema is correct - these columns (`session_id`, `user_id`) were never meant to exist
- The API code was incorrect from the start
- A previous fix may have partially addressed this, but clearly not completely
- This audit verifies EVERYTHING to ensure no issues remain
