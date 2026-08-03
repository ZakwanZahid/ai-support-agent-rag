export const queryKeys = {
  currentUser: ["auth", "me"] as const,
  organizations: ["organizations"] as const,
  knowledgeBases: (organizationId: string | null | undefined) =>
    ["knowledge-bases", organizationId] as const,
  knowledgeBase: (
    organizationId: string | null | undefined,
    knowledgeBaseId: string,
  ) => ["knowledge-bases", organizationId, knowledgeBaseId] as const,
  documents: (
    organizationId: string | null | undefined,
    knowledgeBaseId?: string | null,
  ) => ["documents", organizationId, knowledgeBaseId ?? "all"] as const,
  document: (
    organizationId: string | null | undefined,
    documentId: string,
  ) => ["documents", organizationId, documentId] as const,
  conversations: (organizationId: string | null | undefined) =>
    ["conversations", organizationId] as const,
  conversation: (
    organizationId: string | null | undefined,
    conversationId: string,
  ) => ["conversations", organizationId, conversationId] as const,
};
