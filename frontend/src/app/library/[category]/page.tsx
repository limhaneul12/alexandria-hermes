import { LibraryClient } from "@/components/library/library-client";

type CategoryPageProps = {
  params: Promise<{ category: string }>;
};

export default async function CategoryLibraryPage({ params }: CategoryPageProps) {
  const { category } = await params;
  return <LibraryClient initialCategory={decodeURIComponent(category)} />;
}
