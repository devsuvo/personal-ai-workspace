import type {
  ArtifactItem,
  ArtifactType,
  ProjectSummary,
  UploadedFileDetail,
  UploadedFileMetadata,
} from '../types/workspace';
import { API_BASE_URL, ApiClientError, apiRequest } from './apiClient';

// --- Projects ---

export async function fetchProjects(
  search = '',
  includeArchived = false
): Promise<ProjectSummary[]> {
  const params = new URLSearchParams({
    include_archived: includeArchived ? 'true' : 'false',
  });
  if (search.trim()) params.set('search', search.trim());
  const res = await apiRequest<{ projects: ProjectSummary[] }>(
    `/projects?${params.toString()}`
  );
  return res.projects;
}

export function createProject(payload: {
  name: string;
  description?: string;
  instructions?: string;
  icon?: string;
  color?: string;
}): Promise<ProjectSummary> {
  return apiRequest<ProjectSummary>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateProject(
  projectId: string,
  payload: {
    name?: string;
    description?: string;
    instructions?: string;
    icon?: string;
    color?: string;
  }
): Promise<ProjectSummary> {
  return apiRequest<ProjectSummary>(
    `/projects/${encodeURIComponent(projectId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export function archiveProject(projectId: string): Promise<ProjectSummary> {
  return apiRequest<ProjectSummary>(
    `/projects/${encodeURIComponent(projectId)}/archive`,
    { method: 'POST' }
  );
}

export function restoreProject(projectId: string): Promise<ProjectSummary> {
  return apiRequest<ProjectSummary>(
    `/projects/${encodeURIComponent(projectId)}/restore`,
    { method: 'POST' }
  );
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/projects/${encodeURIComponent(projectId)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) throw new Error(`Failed to delete project (HTTP ${res.status})`);
}

// --- Files ---

export async function fetchFiles(opts?: {
  projectId?: string;
  conversationId?: string;
  search?: string;
}): Promise<UploadedFileMetadata[]> {
  const params = new URLSearchParams();
  if (opts?.projectId) params.set('project_id', opts.projectId);
  if (opts?.conversationId) params.set('conversation_id', opts.conversationId);
  if (opts?.search?.trim()) params.set('search', opts.search.trim());
  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await apiRequest<{ files: UploadedFileMetadata[] }>(
    `/files${query}`
  );
  return res.files;
}

export async function uploadLocalFile(
  file: File,
  opts?: { projectId?: string; conversationId?: string }
): Promise<UploadedFileDetail> {
  const form = new FormData();
  form.append('file', file);
  if (opts?.projectId) form.append('project_id', opts.projectId);
  if (opts?.conversationId) form.append('conversation_id', opts.conversationId);

  const res = await fetch(`${API_BASE_URL}/files/upload`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    let message = `Upload failed (HTTP ${res.status})`;
    try {
      const err = await res.json();
      if (err?.error?.message) message = err.error.message;
    } catch {
      // ignore
    }
    throw new ApiClientError(message, res.status, 'UPLOAD_ERROR');
  }
  return (await res.json()) as UploadedFileDetail;
}

export function fetchFileDetail(fileId: string): Promise<UploadedFileDetail> {
  return apiRequest<UploadedFileDetail>(`/files/${encodeURIComponent(fileId)}`);
}

export function updateFileMetadata(
  fileId: string,
  payload: { original_filename?: string; project_id?: string | null }
): Promise<UploadedFileDetail> {
  return apiRequest<UploadedFileDetail>(`/files/${encodeURIComponent(fileId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function reExtractFile(fileId: string): Promise<UploadedFileDetail> {
  return apiRequest<UploadedFileDetail>(
    `/files/${encodeURIComponent(fileId)}/extract`,
    { method: 'POST' }
  );
}

export async function deleteUploadedFile(fileId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/files/${encodeURIComponent(fileId)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) throw new Error(`Failed to delete file (HTTP ${res.status})`);
}

export function getFileDownloadUrl(fileId: string): string {
  return `${API_BASE_URL}/files/${encodeURIComponent(fileId)}/download`;
}

// --- Artifacts ---

export async function fetchArtifacts(opts?: {
  projectId?: string;
  artifactType?: string;
  search?: string;
}): Promise<ArtifactItem[]> {
  const params = new URLSearchParams();
  if (opts?.projectId) params.set('project_id', opts.projectId);
  if (opts?.artifactType) params.set('artifact_type', opts.artifactType);
  if (opts?.search?.trim()) params.set('search', opts.search.trim());
  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await apiRequest<{ artifacts: ArtifactItem[] }>(
    `/artifacts${query}`
  );
  return res.artifacts;
}

export function createArtifact(payload: {
  title: string;
  artifact_type: ArtifactType;
  content: string;
  language?: string | null;
  project_id?: string | null;
  conversation_id?: string | null;
}): Promise<ArtifactItem> {
  return apiRequest<ArtifactItem>('/artifacts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateArtifact(
  artifactId: string,
  payload: {
    title?: string;
    artifact_type?: ArtifactType;
    content?: string;
    language?: string | null;
    project_id?: string | null;
  }
): Promise<ArtifactItem> {
  return apiRequest<ArtifactItem>(
    `/artifacts/${encodeURIComponent(artifactId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export function duplicateArtifact(artifactId: string): Promise<ArtifactItem> {
  return apiRequest<ArtifactItem>(
    `/artifacts/${encodeURIComponent(artifactId)}/duplicate`,
    { method: 'POST' }
  );
}

export async function deleteArtifact(artifactId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/artifacts/${encodeURIComponent(artifactId)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) throw new Error(`Failed to delete artifact (HTTP ${res.status})`);
}

export function getArtifactExportUrl(artifactId: string): string {
  return `${API_BASE_URL}/artifacts/${encodeURIComponent(artifactId)}/export`;
}
