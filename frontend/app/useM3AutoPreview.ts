import { useMemo } from "react";
import { M3_FULL_SECTIONS, M3_SECTION_TITLE_ALIASES } from "./constants";

export interface M3AutoPreviewResult {
  grouped: Array<{
    title: string;
    textField: string;
    imageField: string;
    files: Array<{ filename: string; parsed: { title: string; imageField: string; order: number; label: string } | null; isTable: boolean }>;
    tables: Array<{ filename: string; parsed: { title: string; imageField: string; order: number; label: string } | null; isTable: boolean }>;
    descriptions: Array<{ line: string; parsed: { title: string; imageField: string; order: number; label: string } | null; valid: boolean }>;
  }>;
  unknownFiles: string[];
  invalidDescriptions: string[];
}

export function useM3AutoPreview(files: File[], descriptions: string): M3AutoPreviewResult {
  return useMemo(() => {
    const normalize = (value: string) => value.trim().replace(/\s+/g, "");
    const parseImageKey = (value: string) => {
      const normalized = normalize(value);
      const match = normalized.match(/^(.+?)(?:-(\d+))?$/);
      if (!match) return null;
      const section = M3_FULL_SECTIONS.find((item) => item.title === match[1]);
      if (!section) return null;
      return { title: section.title, imageField: section.imageField, order: match[2] ? Number(match[2]) : -1, label: normalized };
    };
    const parseTableKey = (value: string) => {
      const normalized = normalize(value);
      const aliased = Object.entries(M3_SECTION_TITLE_ALIASES).reduce((current, [alias, canonical]) => {
        const normalizedAlias = normalize(alias);
        const normalizedCanonical = normalize(canonical);
        if (current === normalizedAlias) return normalizedCanonical;
        if (current.startsWith(`${normalizedAlias}-`)) return `${normalizedCanonical}-${current.slice(normalizedAlias.length + 1)}`;
        return current;
      }, normalized);
      const section = M3_FULL_SECTIONS.find((item) => aliased === item.title || aliased.startsWith(`${item.title}-`));
      if (!section) return null;
      return { title: section.title, imageField: section.imageField, order: -1, label: normalized };
    };
    const fileRows = files.map((file) => {
      const nameWithoutExt = file.name.replace(/\.[^.]+$/, "");
      const isTable = /\.xlsx$/i.test(file.name);
      const parsed = isTable ? parseTableKey(nameWithoutExt) : parseImageKey(nameWithoutExt);
      return { filename: file.name, parsed, isTable };
    });
    const descriptionRows = descriptions
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const match = line.match(/^([^:：]+)[:：](.*)$/);
        const parsed = match ? parseImageKey(match[1]) : null;
        return { line, parsed, valid: Boolean(match && parsed) };
      });
    const grouped = M3_FULL_SECTIONS.map((section) => ({
      ...section,
      files: fileRows
        .filter((row) => row.parsed?.imageField === section.imageField && !row.isTable)
        .sort((a, b) => (a.parsed?.order ?? 0) - (b.parsed?.order ?? 0)),
      tables: fileRows.filter((row) => row.parsed?.imageField === section.imageField && row.isTable),
      descriptions: descriptionRows.filter((row) => row.parsed?.imageField === section.imageField),
    })).filter((section) => section.files.length || section.tables.length || section.descriptions.length);
    return {
      grouped,
      unknownFiles: fileRows.filter((row) => !row.parsed).map((row) => row.filename),
      invalidDescriptions: descriptionRows.filter((row) => !row.valid).map((row) => row.line),
    };
  }, [files, descriptions]);
}
