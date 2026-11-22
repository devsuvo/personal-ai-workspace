export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  instructions: string;
  icon: string;
  color: string;
  is_archived: boolean;
  conversations_count: number;
  files_count: number;
  artifacts_count: number;
  created_at: string;
  updated_at: string;
}

export interface UploadedFileMetadata {
  id: string;
  project_id: string | null;
  conversation_id: string | null;
  original_filename: string;
  mime_type: string;
  file_size: number;
  extraction_status: 'pending' | 'completed' | 'ocr_required' | 'unsupported' | 'failed' | string;
  extraction_error: string | null;
  has_extracted_text: boolean;
  is_image: boolean;
  created_at: string;
}

export interface UploadedFileDetail extends UploadedFileMetadata {
  extracted_text_preview: string | null;
}

export type ArtifactType =
  | 'document'
  | 'markdown'
  | 'code'
  | 'html'
  | 'json'
  | 'table'
  | 'csv'
  | 'text';

export interface ArtifactItem {
  id: string;
  project_id: string | null;
  conversation_id: string | null;
  title: string;
  artifact_type: ArtifactType | string;
  content: string;
  language: string | null;
  created_at: string;
  updated_at: string;
}
