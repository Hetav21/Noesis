import { ResearchWorkspace } from "@/components/ResearchWorkspace";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ResearchDetailPage({ params }: PageProps) {
  const resolved = await params;
  return <ResearchWorkspace key={resolved.id} jobId={resolved.id} />;
}
