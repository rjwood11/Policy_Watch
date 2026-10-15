import type { Metadata } from "next";
import { GLOSSARY, glossaryId } from "@/lib/glossary";

export const metadata: Metadata = {
  title: "Acronyms and map terms | PolicyWatch",
  description: "Plain-language explanations of water, mapping, and agency acronyms used in PolicyWatch."
};

export default function GlossaryPage() {
  return (
    <div className="shell space-y-6 py-10">
      <div className="max-w-3xl">
        <p className="text-xs uppercase tracking-normal text-river">Glossary</p>
        <h1 className="mt-2 text-3xl font-semibold">Acronyms and map terms</h1>
        <p className="mt-4 text-sm leading-7 text-ink/75">
          A quick reference for the agencies, datasets, and compliance terms used throughout
          Water Policy Watch. Dotted-underlined abbreviations also offer a hover explanation;
          this page provides the same reference on phones and with a keyboard.
        </p>
      </div>
      <nav aria-label="Jump to an acronym" className="card flex flex-wrap gap-x-5 gap-y-3 p-5 text-sm">
        {GLOSSARY.map((entry) => <a key={entry.term} href={`#${glossaryId(entry.term)}`}>{entry.term}</a>)}
      </nav>
      <dl className="card divide-y divide-ink/10 px-6">
        {GLOSSARY.map((entry) => (
          <div key={entry.term} id={glossaryId(entry.term)} className="scroll-mt-6 py-5">
            <dt className="font-semibold text-ink">{entry.term} — {entry.name}</dt>
            <dd className="mt-2 max-w-4xl text-sm leading-7 text-ink/75">
              {entry.meaning}
              {"source" in entry && (
                <> <a href={entry.source} target="_blank" rel="noreferrer">Agency reference</a></>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
