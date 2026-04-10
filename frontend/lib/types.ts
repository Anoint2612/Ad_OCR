export interface UploadResponse {
  job_id: string;
  image_count: number;
}

export interface ExtractedText {
  headline: string;
  subheadline: string;
  cta: string;
  offer: string;
  brand_name: string;
  raw_lines: string[];
  confidence_avg: number;
}

export interface VisualDescription {
  product_type: string;
  layout: string;
  colors: string[];
  style: string;
  background: string;
  extras: string[];
  _fallback?: boolean;
}

export interface AdAnalysis {
  image_id: string;
  image_path: string;
  extracted_text: ExtractedText;
  visual_description: VisualDescription;
  job_id?: string;
}

export interface PatternReport {
  summary: string;
  common_layouts: string[];
  recurring_palettes: string[];
  style_patterns: string[];
  copy_tone: string;
  cta_patterns: string[];
}

export interface TemplateResponse {
  template: string;
  variables: string[];
}

export interface GenerateRequest {
  job_id: string;
  inputs: Record<string, string>;
}

export interface GenerateResponse {
  prompt: string;
}

export interface AnalyzeResponse {
  analyses: AdAnalysis[];
}

export interface HealthResponse {
  status: string;
  database_available: boolean;
  ollama_available: boolean;
  vision_model: string;
  llm_model: string;
}
