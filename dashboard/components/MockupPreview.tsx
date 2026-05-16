import type { GeneratedSiteRow } from "@/lib/types";

type MockupPreviewProps = {
  site: GeneratedSiteRow;
};

function publicUrl(site: GeneratedSiteRow) {
  return site.vercel_url || site.storage_url;
}

export function MockupPreview({ site }: MockupPreviewProps) {
  const url = publicUrl(site);
  return (
    <article
      className={`rounded-lg border bg-white shadow-sm ${
        site.is_chosen_winner ? "border-emerald-300 ring-2 ring-emerald-100" : "border-slate-200"
      }`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">{site.variant.replaceAll("_", " ")}</h3>
          <p className="mt-1 text-xs text-slate-500">
            Score {site.self_critique_score ?? "-"}/10 / {site.self_critique_iterations ?? 1} iteration
          </p>
        </div>
        {site.is_chosen_winner && (
          <span className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">Winner</span>
        )}
      </div>
      <div className="aspect-video overflow-hidden bg-slate-100">
        {url ? (
          <iframe className="h-full w-full" src={url} title={`${site.variant} mockup`} />
        ) : site.html_content ? (
          <iframe className="h-full w-full" srcDoc={site.html_content} title={`${site.variant} mockup`} />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">No preview available.</div>
        )}
      </div>
      <div className="space-y-2 px-4 py-3 text-xs text-slate-600">
        {url && (
          <a className="font-medium text-sky-700 underline-offset-2 hover:underline" href={url} target="_blank" rel="noreferrer">
            Open mockup
          </a>
        )}
        {site.pick_reasoning && <p>{site.pick_reasoning}</p>}
        {site.critique_issues && site.critique_issues.length > 0 && (
          <p>Issues: {site.critique_issues.join(", ")}</p>
        )}
      </div>
    </article>
  );
}
