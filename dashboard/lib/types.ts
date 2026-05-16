export type ClawName = "scout" | "designer" | "pitcher" | "closer" | (string & {});

export type ActionStatus = "started" | "succeeded" | "failed" | "skipped" | (string & {});

export type QualificationStatus =
  | "pending"
  | "qualified_for_mockup"
  | "qualified_for_rebuild"
  | "skip"
  | (string & {});

export type LeadRow = {
  id: string;
  business_name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  niche: string;
  city: string;
  google_rating: number | null;
  review_count: number | null;
  review_texts: string[] | null;
  top_review_pain_points: string[] | null;
  website_score: number | null;
  website_score_reasons: string[] | null;
  qualification_status: QualificationStatus;
  qualification_reason: string | null;
  worked_by_designer: boolean | null;
  worked_by_pitcher: boolean | null;
  do_not_contact: boolean | null;
  scraped_at: string | null;
  updated_at: string | null;
};

export type ActionRow = {
  id: string;
  claw_name: ClawName;
  lead_id: string | null;
  action_type: string;
  status: ActionStatus;
  started_at: string | null;
  finished_at: string | null;
  result_json: Record<string, unknown> | null;
  human_readable_log: string;
};

export type GeneratedSiteRow = {
  id: string;
  lead_id: string;
  variant: string;
  vercel_url: string | null;
  storage_url: string | null;
  html_content: string;
  self_critique_score: number | null;
  self_critique_iterations: number | null;
  critique_issues: string[] | null;
  is_chosen_winner: boolean | null;
  pick_reasoning: string | null;
  generated_at: string | null;
};

export type DashboardMetrics = {
  totalLeads: number;
  qualifiedLeads: number;
  sitesGenerated: number;
  outreachSent: number;
  repliesReceived: number;
  meetingsBooked: number;
};

export type Database = {
  public: {
    Tables: {
      leads: {
        Row: LeadRow;
        Insert: Partial<LeadRow>;
        Update: Partial<LeadRow>;
      };
      actions: {
        Row: ActionRow;
        Insert: Partial<ActionRow>;
        Update: Partial<ActionRow>;
      };
      generated_sites: {
        Row: GeneratedSiteRow;
        Insert: Partial<GeneratedSiteRow>;
        Update: Partial<GeneratedSiteRow>;
      };
      outreach: {
        Row: { id: string; status: string; sent_at: string | null };
        Insert: Record<string, unknown>;
        Update: Record<string, unknown>;
      };
      inbound: {
        Row: { id: string; received_at: string | null };
        Insert: Record<string, unknown>;
        Update: Record<string, unknown>;
      };
      meetings: {
        Row: { id: string; status: string; booked_at: string | null };
        Insert: Record<string, unknown>;
        Update: Record<string, unknown>;
      };
    };
  };
};
