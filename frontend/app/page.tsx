"use client";

import { useMemo, useState } from "react";

import {
  analyzeAds,
  checkHealth,
  generatePrompt,
  getPatterns,
  getTemplate,
  uploadAds,
} from "@/lib/api";
import type {
  AdAnalysis,
  PatternReport,
  TemplateResponse,
} from "@/lib/types";

type WizardStep = 1 | 2 | 3 | 4;

type InputState = {
  product_name: string;
  product_benefit: string;
  cta_text: string;
  target_audience: string;
  headline: string;
};

const STEP_LABELS: Record<WizardStep, string> = {
  1: "Upload",
  2: "Analysis",
  3: "Patterns",
  4: "Generate",
};

const acceptedExt = [".jpg", ".jpeg", ".png", ".webp"];

export default function Page() {
  const [step, setStep] = useState<WizardStep>(1);
  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string>("");

  const [analyses, setAnalyses] = useState<AdAnalysis[]>([]);
  const [patternReport, setPatternReport] = useState<PatternReport | null>(null);
  const [templateData, setTemplateData] = useState<TemplateResponse | null>(null);
  const [finalPrompt, setFinalPrompt] = useState<string>("");

  const [inputs, setInputs] = useState<InputState>({
    product_name: "",
    product_benefit: "",
    cta_text: "",
    target_audience: "",
    headline: "",
  });

  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPatternsLoading, setIsPatternsLoading] = useState(false);
  const [isTemplateLoading, setIsTemplateLoading] = useState(false);
  const [isPromptLoading, setIsPromptLoading] = useState(false);
  const [isHealthLoading, setIsHealthLoading] = useState(false);

  const [error, setError] = useState<string>("");
  const [copied, setCopied] = useState(false);

  const previewUrls = useMemo(
    () => files.map((file) => ({ name: file.name, url: URL.createObjectURL(file) })),
    [files]
  );

  const totalSteps: WizardStep[] = [1, 2, 3, 4];

  function setInlineError(message: string) {
    setError(message);
  }

  function validateSelection(selected: File[]): string | null {
    if (selected.length < 1 || selected.length > 10) {
      return "Please select between 1 and 10 images.";
    }

    for (const file of selected) {
      const lower = file.name.toLowerCase();
      const valid = acceptedExt.some((ext) => lower.endsWith(ext));
      if (!valid) {
        return `Unsupported file type: ${file.name}. Allowed: jpg, jpeg, png, webp.`;
      }
    }

    return null;
  }

  function onSelectFiles(list: FileList | null) {
    if (!list) {
      return;
    }
    const selected = Array.from(list);
    const validationError = validateSelection(selected);
    if (validationError) {
      setInlineError(validationError);
      return;
    }
    setError("");
    setFiles(selected);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    onSelectFiles(event.dataTransfer.files);
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
  }

  async function handleAnalyzeAds() {
    if (files.length === 0) {
      setInlineError("Please upload at least one image.");
      return;
    }

    setError("");
    setIsUploading(true);
    try {
      const uploadResult = await uploadAds(files);
      setJobId(uploadResult.job_id);
      setStep(2);

      setIsAnalyzing(true);
      const analysisResult = await analyzeAds(uploadResult.job_id);
      setAnalyses(analysisResult.analyses ?? []);
    } catch (err) {
      setInlineError(err instanceof Error ? err.message : "Failed to analyze ads.");
    } finally {
      setIsUploading(false);
      setIsAnalyzing(false);
    }
  }

  async function handleExtractPatterns() {
    if (!jobId) {
      setInlineError("Job ID missing. Upload and analyze ads first.");
      return;
    }

    setError("");
    setIsPatternsLoading(true);
    try {
      const report = await getPatterns(jobId);
      setPatternReport(report);
      setStep(3);
    } catch (err) {
      setInlineError(
        err instanceof Error ? err.message : "Failed to extract patterns."
      );
    } finally {
      setIsPatternsLoading(false);
    }
  }

  async function handleGenerateTemplate() {
    if (!jobId) {
      setInlineError("Job ID missing. Run previous steps first.");
      return;
    }

    setError("");
    setIsTemplateLoading(true);
    try {
      const template = await getTemplate(jobId);
      setTemplateData(template);
      setStep(4);
    } catch (err) {
      setInlineError(
        err instanceof Error ? err.message : "Failed to generate template."
      );
    } finally {
      setIsTemplateLoading(false);
    }
  }

  async function handleGeneratePrompt() {
    if (!jobId || !templateData?.template) {
      setInlineError("Template missing. Run /prompt/template flow first.");
      return;
    }

    setError("");
    setIsPromptLoading(true);
    setCopied(false);
    try {
      const response = await generatePrompt(jobId, inputs);
      setFinalPrompt(response.prompt);
    } catch (err) {
      setInlineError(err instanceof Error ? err.message : "Failed to generate prompt.");
    } finally {
      setIsPromptLoading(false);
    }
  }

  async function handleCopyPrompt() {
    if (!finalPrompt) return;
    await navigator.clipboard.writeText(finalPrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function handleHealthCheck() {
    setIsHealthLoading(true);
    setError("");
    try {
      const health = await checkHealth();
      alert(
        `Status: ${health.status}\nDB: ${health.database_available}\nOllama: ${health.ollama_available}\nVision: ${health.vision_model}\nLLM: ${health.llm_model}`
      );
    } catch (err) {
      setInlineError(err instanceof Error ? err.message : "Health check failed.");
    } finally {
      setIsHealthLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Ad Prompt Intelligence
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Upload ad creatives, extract patterns, and generate reusable prompts.
            </p>
            {jobId ? (
              <p className="mt-2 text-xs text-slate-500">Current Job ID: {jobId}</p>
            ) : null}
          </div>

          <button
            type="button"
            onClick={handleHealthCheck}
            className="inline-flex items-center justify-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {isHealthLoading ? <Spinner small /> : null}
            <span className={isHealthLoading ? "ml-2" : ""}>Check Health</span>
          </button>
        </div>
      </header>

      <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap gap-2">
          {totalSteps.map((item) => {
            const active = item === step;
            const complete = item < step;
            return (
              <div
                key={item}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ${
                  active
                    ? "bg-blue-600 text-white"
                    : complete
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                <span>{item}</span>
                <span>{STEP_LABELS[item]}</span>
              </div>
            );
          })}
        </div>
      </section>

      {error ? (
        <div className="mb-6 rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <section className="grid gap-6">
        {step === 1 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Step 1: Upload Ads</h2>
            <p className="mt-1 text-sm text-slate-600">
              Drag and drop 1-10 ad images (jpg, jpeg, png, webp).
            </p>

            <div
              className="mt-4 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              <p className="text-sm text-slate-600">Drop images here or select files</p>
              <label className="mt-4 inline-flex cursor-pointer rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
                Choose Files
                <input
                  type="file"
                  className="hidden"
                  accept=".jpg,.jpeg,.png,.webp"
                  multiple
                  onChange={(event) => onSelectFiles(event.target.files)}
                />
              </label>
            </div>

            {previewUrls.length > 0 ? (
              <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
                {previewUrls.map((item) => (
                  <div key={item.name} className="rounded-lg border border-slate-200 p-2">
                    <img
                      src={item.url}
                      alt={item.name}
                      className="h-24 w-full rounded object-cover"
                    />
                    <p className="mt-2 truncate text-xs text-slate-600">{item.name}</p>
                  </div>
                ))}
              </div>
            ) : null}

            <div className="mt-6">
              <button
                type="button"
                onClick={handleAnalyzeAds}
                disabled={isUploading || isAnalyzing || files.length === 0}
                className="inline-flex items-center rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isUploading || isAnalyzing ? <Spinner small /> : null}
                <span className={isUploading || isAnalyzing ? "ml-2" : ""}>
                  {isUploading || isAnalyzing ? "Analyzing Ads..." : "Analyze Ads"}
                </span>
              </button>
            </div>
          </div>
        ) : null}

        {step >= 2 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Step 2: Analysis</h2>
                <p className="text-sm text-slate-600">
                  OCR and visual analysis results for each uploaded ad.
                </p>
              </div>
              <button
                type="button"
                onClick={handleExtractPatterns}
                disabled={isPatternsLoading || analyses.length === 0}
                className="inline-flex items-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isPatternsLoading ? <Spinner small /> : null}
                <span className={isPatternsLoading ? "ml-2" : ""}>Extract Patterns</span>
              </button>
            </div>

            {isAnalyzing ? (
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <Spinner small />
                <span>Running analysis...</span>
              </div>
            ) : analyses.length === 0 ? (
              <p className="text-sm text-slate-500">No analyses yet.</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {analyses.map((analysis) => (
                  <article
                    key={analysis.image_id}
                    className="rounded-xl border border-slate-200 p-4"
                  >
                    <h3 className="text-sm font-semibold text-slate-900">
                      Ad #{analysis.image_id.slice(0, 8)}
                    </h3>

                    <div className="mt-3 space-y-1 text-sm text-slate-700">
                      <p>
                        <span className="font-medium">Headline:</span>{" "}
                        {analysis.extracted_text?.headline || "-"}
                      </p>
                      <p>
                        <span className="font-medium">CTA:</span>{" "}
                        {analysis.extracted_text?.cta || "-"}
                      </p>
                      <p>
                        <span className="font-medium">Offer:</span>{" "}
                        {analysis.extracted_text?.offer || "-"}
                      </p>
                    </div>

                    <div className="mt-3 space-y-1 text-sm text-slate-700">
                      <p>
                        <span className="font-medium">Product Type:</span>{" "}
                        {analysis.visual_description?.product_type || "-"}
                      </p>
                      <p>
                        <span className="font-medium">Style:</span>{" "}
                        {analysis.visual_description?.style || "-"}
                      </p>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {(analysis.visual_description?.colors || []).map((color, idx) => (
                        <span
                          key={`${analysis.image_id}-${color}-${idx}`}
                          className="rounded-full border border-slate-300 px-2 py-1 text-xs text-slate-700"
                          title={color}
                          style={{ backgroundColor: normalizeColor(color) }}
                        >
                          {color}
                        </span>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        ) : null}

        {step >= 3 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900">Step 3: Patterns</h2>
                <p className="text-sm text-slate-600">Cross-ad creative patterns detected.</p>
              </div>
              <button
                type="button"
                onClick={handleGenerateTemplate}
                disabled={!patternReport || isTemplateLoading}
                className="inline-flex items-center rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isTemplateLoading ? <Spinner small /> : null}
                <span className={isTemplateLoading ? "ml-2" : ""}>Generate Template</span>
              </button>
            </div>

            {!patternReport ? (
              <p className="text-sm text-slate-500">No pattern report yet.</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <InfoCard title="Summary" content={patternReport.summary} />
                <InfoCard title="Copy Tone" content={patternReport.copy_tone} />
                <InfoCard title="Common Layouts" list={patternReport.common_layouts} />
                <InfoCard
                  title="Recurring Palettes"
                  list={patternReport.recurring_palettes}
                />
                <InfoCard title="Style Patterns" list={patternReport.style_patterns} />
                <InfoCard title="CTA Patterns" list={patternReport.cta_patterns} />
              </div>
            )}
          </div>
        ) : null}

        {step >= 4 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Step 4: Generate Prompt</h2>
            <p className="mt-1 text-sm text-slate-600">
              Fill template variables and generate the final prompt.
            </p>

            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <h3 className="mb-2 text-sm font-medium text-slate-800">Template Preview</h3>
              <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">
                {highlightTemplate(templateData?.template ?? "")}
              </p>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <InputField
                label="Product Name"
                value={inputs.product_name}
                onChange={(value) => setInputs((prev) => ({ ...prev, product_name: value }))}
              />
              <InputField
                label="Product Benefit"
                value={inputs.product_benefit}
                onChange={(value) =>
                  setInputs((prev) => ({ ...prev, product_benefit: value }))
                }
              />
              <InputField
                label="CTA Text"
                value={inputs.cta_text}
                onChange={(value) => setInputs((prev) => ({ ...prev, cta_text: value }))}
              />
              <InputField
                label="Target Audience"
                value={inputs.target_audience}
                onChange={(value) =>
                  setInputs((prev) => ({ ...prev, target_audience: value }))
                }
              />
              <div className="md:col-span-2">
                <InputField
                  label="Headline"
                  value={inputs.headline}
                  onChange={(value) => setInputs((prev) => ({ ...prev, headline: value }))}
                />
              </div>
            </div>

            <div className="mt-5">
              <button
                type="button"
                onClick={handleGeneratePrompt}
                disabled={isPromptLoading || !templateData}
                className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isPromptLoading ? <Spinner small /> : null}
                <span className={isPromptLoading ? "ml-2" : ""}>Generate Prompt</span>
              </button>
            </div>

            <div className="mt-5">
              <label className="mb-2 block text-sm font-medium text-slate-800">
                Final Prompt
              </label>
              <textarea
                value={finalPrompt}
                onChange={(event) => setFinalPrompt(event.target.value)}
                rows={8}
                className="w-full rounded-xl border border-slate-300 p-3 text-sm text-slate-800 focus:border-blue-500 focus:outline-none"
                placeholder="Generated prompt will appear here..."
              />
              <div className="mt-2">
                <button
                  type="button"
                  onClick={handleCopyPrompt}
                  disabled={!finalPrompt}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}

function Spinner({ small = false }: { small?: boolean }) {
  return (
    <span
      className={`${small ? "h-4 w-4" : "h-5 w-5"} inline-block animate-spin rounded-full border-2 border-white border-r-transparent`}
    />
  );
}

function InfoCard({
  title,
  content,
  list,
}: {
  title: string;
  content?: string;
  list?: string[];
}) {
  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
      {content ? <p className="mt-2 text-sm text-slate-700">{content}</p> : null}
      {list?.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {list.map((item, idx) => (
            <li key={`${item}-${idx}`}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-800">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none"
      />
    </label>
  );
}

function highlightTemplate(template: string) {
  if (!template) {
    return <span className="text-slate-500">No template generated yet.</span>;
  }

  const segments = template.split(/(\[[A-Z_]+\])/g);
  return segments.map((segment, index) => {
    if (/^\[[A-Z_]+\]$/.test(segment)) {
      return (
        <span
          key={`${segment}-${index}`}
          className="rounded bg-blue-100 px-1 py-0.5 font-medium text-blue-700"
        >
          {segment}
        </span>
      );
    }
    return <span key={`${segment}-${index}`}>{segment}</span>;
  });
}

function normalizeColor(color: string): string {
  const value = color.trim().toLowerCase();
  const fallback = "#f1f5f9";
  if (!value) return fallback;

  if (
    value.startsWith("#") ||
    value.startsWith("rgb") ||
    /^[a-z]+$/.test(value)
  ) {
    return value;
  }

  return fallback;
}
