"use client";

import type { FormEventHandler } from "react";
import { FolderPlus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { t } from "@/lib/i18n";
import type { CategoryOption } from "@/lib/library/forms";
import { useLibraryStore } from "@/store/library-store";

export function CategorySelect({
  label,
  value,
  options,
  emptyLabel,
  name,
  onChange,
}: {
  label: string;
  value: string;
  options: CategoryOption[];
  emptyLabel: string;
  name: string;
  onChange: (value: string) => void;
}) {
  return (
    <Select
      name={name}
      label={label}
      value={value}
      onChange={onChange}
      options={[
        { value: "", label: emptyLabel },
        ...options.map((category) => ({ value: category.id, label: category.label })),
      ]}
    />
  );
}

export function FolderCreateForm({
  name,
  parentId,
  options,
  isPending,
  onNameChange,
  onParentChange,
  onSubmit,
}: {
  name: string;
  parentId: string;
  options: CategoryOption[];
  isPending: boolean;
  onNameChange: (value: string) => void;
  onParentChange: (value: string) => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
}) {
  const language = useLibraryStore((state) => state.language);

  return (
    <form onSubmit={onSubmit} className="archive-paper-card mb-6 space-y-4 p-5">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#111111]">{t(language, "newFolder")}</p>
        <p className="mt-1 text-sm text-[#6f6a60]">{t(language, "folderCreateHelper")}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">
          {t(language, "folderName")}
          <Input name="folderName" autoComplete="off" value={name} onChange={(event) => onNameChange(event.target.value)} placeholder={t(language, "folderNamePlaceholder")} required className="mt-2" />
        </label>
        <CategorySelect label={t(language, "parentFolder")} name="parentFolder" value={parentId} options={options} emptyLabel={t(language, "rootFolder")} onChange={onParentChange} />
      </div>
      <Button type="submit" size="sm" disabled={isPending || !name.trim()}>
        <FolderPlus className="h-3.5 w-3.5" aria-hidden="true" /> {t(language, "createFolder")}
      </Button>
    </form>
  );
}
