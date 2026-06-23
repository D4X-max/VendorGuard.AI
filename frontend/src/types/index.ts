// ─── Auth ───────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  tenant_id: string;
  is_active: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// ─── Vendors ────────────────────────────────────────────
export type CriticalityTier = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface Vendor {
  id: string;
  tenant_id: string;
  legal_name: string;
  domain: string;
  criticality_tier: CriticalityTier;
  stores_customer_data: boolean;
  access_production_systems: boolean;
  handles_payments: boolean;
  handles_phi_pii: boolean;
  overall_inherent_score: number;
  created_at: string;
  updated_at: string;
}

export interface VendorCreate {
  legal_name: string;
  domain: string;
  criticality_tier: CriticalityTier;
  stores_customer_data: boolean;
  access_production_systems: boolean;
  handles_payments: boolean;
  handles_phi_pii: boolean;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

// ─── Findings ───────────────────────────────────────────
export type FindingStatus = 'DRAFT' | 'REVIEWED' | 'APPROVED' | 'REJECTED';
export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface Finding {
  id: string;
  tenant_id: string;
  vendor_id: string;
  title: string;
  description: string;
  severity_level: SeverityLevel;
  status: FindingStatus;
  ai_confidence_score: number | null;
  ai_reasoning_rationale: string | null;
  identified_at: string;
  updated_at: string;
}

export interface FindingCreate {
  vendor_id: string;
  title: string;
  description: string;
  severity_level: SeverityLevel;
}

// ─── Risk ────────────────────────────────────────────────
export interface RiskProfile {
  vendor_id: string;
  inherent_risk_score: number;
  residual_risk_score: number;
  risk_appetite_status: 'WITHIN_APPETITE' | 'EXCEEDS_APPETITE';
  treatment_strategy: 'MITIGATE' | 'ACCEPT' | 'TRANSFER' | 'AVOID';
  next_review_date: string;
  created_at: string;
  updated_at: string;
}

export interface RiskSummary {
  total_vendors_assessed: number;
  exceeds_appetite: number;
  within_appetite: number;
  vendors: RiskProfile[];
}

// ─── Evidence ────────────────────────────────────────────
export type ProcessingStatus = 'PENDING' | 'COMPLETED' | 'FAILED';

export interface EvidenceDocument {
  id: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  processing_status: ProcessingStatus;
  created_at: string;
}