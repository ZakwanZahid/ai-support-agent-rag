import { BookOpen, FileCheck2, FileText, MessagesSquare } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface StatCardsProps {
  knowledgeSpaces: number;
  documents: number;
  readyDocuments: number;
  chatThreads: number;
}

export function StatCards({
  knowledgeSpaces,
  documents,
  readyDocuments,
  chatThreads,
}: StatCardsProps) {
  const stats = [
    { label: "Knowledge spaces", value: knowledgeSpaces, icon: BookOpen },
    { label: "Documents", value: documents, icon: FileText },
    { label: "Ready for chat", value: readyDocuments, icon: FileCheck2 },
    { label: "Chat threads", value: chatThreads, icon: MessagesSquare },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {stats.map(({ label, value, icon: Icon }) => (
        <Card key={label}>
          <CardContent className="py-5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm text-foreground-muted">{label}</p>
              <Icon
                aria-hidden="true"
                className="size-4 shrink-0 text-foreground-subtle"
              />
            </div>
            <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
              {value}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
