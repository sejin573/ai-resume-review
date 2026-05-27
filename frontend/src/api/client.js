const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "ai_resume_review_token";

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function isAuthFailure(detail) {
  return (
    detail === "Not authenticated" ||
    detail === "Invalid authentication credentials" ||
    detail === "User not found"
  );
}

async function downloadFile(path, fileName) {
  const headers = {};
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (response.status === 401 && token && typeof data === "object" && isAuthFailure(data?.detail)) {
      clearToken();
    }
    const message =
      typeof data === "object" && data?.detail
        ? data.detail
        : "파일을 내려받는 중 오류가 발생했습니다.";
    throw new Error(message);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    if (response.status === 401 && token && typeof data === "object" && isAuthFailure(data?.detail)) {
      clearToken();
    }
    const message =
      typeof data === "object" && data?.detail
        ? data.detail
        : "요청을 처리하는 중 오류가 발생했습니다.";
    throw new Error(message);
  }

  return data;
}

export const api = {
  health: () => request("/health"),
  signup: (payload) => request("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) => request("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/auth/me"),
  getReviews: () => request("/reviews"),
  getReview: (id) => request(`/reviews/${id}`),
  createReview: (payload) => request("/reviews", { method: "POST", body: JSON.stringify(payload) }),
  consentTraining: (id, consentGiven) =>
    request(`/reviews/${id}/consent-training`, {
      method: "POST",
      body: JSON.stringify({ consent_given: consentGiven }),
    }),
  refineReview: (id, payload) =>
    request(`/reviews/${id}/refine`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitReviewFeedback: (id, payload) =>
    request(`/reviews/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getFinalDocument: (id) => request(`/reviews/${id}/final-document`),
  saveFinalDocument: (id, payload) =>
    request(`/reviews/${id}/final-document`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  exportReviewPdf: (id, fileName = "coverfit-final.pdf") => downloadFile(`/reviews/${id}/export/pdf`, fileName),
  getDataSources: () => request("/admin/data-sources"),
  createDataSource: (payload) => request("/admin/data-sources", { method: "POST", body: JSON.stringify(payload) }),
  updateDataSource: (id, payload) =>
    request(`/admin/data-sources/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  importCsv: (dataSourceId, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request(`/admin/import/csv?data_source_id=${encodeURIComponent(dataSourceId)}`, {
      method: "POST",
      body: formData,
    });
  },
  importJsonl: (dataSourceId, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request(`/admin/import/jsonl?data_source_id=${encodeURIComponent(dataSourceId)}`, {
      method: "POST",
      body: formData,
    });
  },
  importApprovedUrls: (payload) =>
    request("/admin/import/approved-urls", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getImportedDocuments: () => request("/admin/imported-documents"),
  getImportedDocument: (id) => request(`/admin/imported-documents/${id}`),
  anonymizeImportedDocument: (id) =>
    request(`/admin/imported-documents/${id}/anonymize`, {
      method: "POST",
    }),
  rejectImportedDocument: (id, rejectionReason) =>
    request(`/admin/imported-documents/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ rejection_reason: rejectionReason }),
    }),
  createTrainingSampleFromDocument: (id) =>
    request(`/admin/imported-documents/${id}/create-training-sample`, {
      method: "POST",
    }),
  getTrainingSamples: () => request("/admin/training-samples"),
  getTrainingSample: (id) => request(`/admin/training-samples/${id}`),
  reviewTrainingSample: (id, payload) =>
    request(`/admin/training-samples/${id}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  exportCuratedTrainingJsonl: () =>
    request("/admin/export/curated-training-jsonl", {
      method: "POST",
    }),
};
