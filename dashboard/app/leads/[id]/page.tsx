import { LeadDetail } from "@/components/LeadDetail";

type LeadDetailPageProps = {
  params: {
    id: string;
  };
};

export default function LeadDetailPage({ params }: LeadDetailPageProps) {
  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <LeadDetail leadId={params.id} />
      </div>
    </main>
  );
}
