import axios, { AxiosError } from "axios";

import type {
  AnalyzeResponse,
  GenerateResponse,
  HealthResponse,
  PatternReport,
  TemplateResponse,
  UploadResponse,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    return (
      axiosError.response?.data?.detail ||
      axiosError.message ||
      "Request failed"
    );
  }
  return error instanceof Error ? error.message : "Unknown error";
}

export async function uploadAds(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  try {
    const { data } = await api.post<UploadResponse>("/ads/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function analyzeAds(jobId: string): Promise<AnalyzeResponse> {
  try {
    const { data } = await api.post<AnalyzeResponse>("/ads/analyze", {
      job_id: jobId,
    });
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function getPatterns(jobId: string): Promise<PatternReport> {
  try {
    const { data } = await api.post<PatternReport>("/ads/patterns", {
      job_id: jobId,
    });
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function getTemplate(jobId: string): Promise<TemplateResponse> {
  try {
    const { data } = await api.post<TemplateResponse>("/prompt/template", {
      job_id: jobId,
    });
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function generatePrompt(
  jobId: string,
  inputs: Record<string, string>
): Promise<GenerateResponse> {
  try {
    const { data } = await api.post<GenerateResponse>("/prompt/generate", {
      job_id: jobId,
      inputs,
    });
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const { data } = await api.get<HealthResponse>("/health");
    return data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}
