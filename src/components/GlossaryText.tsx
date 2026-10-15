import { GLOSSARY } from "@/lib/glossary";

const terms = new Map(GLOSSARY.map((entry) => [entry.term as string, entry]));
const pattern = new RegExp(`\\b(${GLOSSARY.map((entry) => entry.term).join("|")})\\b`, "g");

export function GlossaryText({ text }: { text: string }) {
  return text.split(pattern).map((part, index) => {
    const entry = terms.get(part);
    return entry ? (
      <abbr key={index} title={`${entry.name}. ${entry.meaning}`} className="cursor-help decoration-dotted underline-offset-2">
        {part}
      </abbr>
    ) : part;
  });
}
