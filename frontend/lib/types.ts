/**
 * TypeScript interfaces mirroring all Python Pydantic models.
 */

export type AppType = "crm" | "ecommerce" | "saas" | "dashboard" | "social" | "custom";
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
export type ValidationSeverity = "critical" | "warning";
export type PipelineStatus = "pending" | "running" | "done" | "error";
export type GenerationStatus = "success" | "partial" | "failed";

// ── Intent ────────────────────────────────────────────────────────────────
export interface FeatureSpec {
  name: string;
  description: string;
  priority: "high" | "medium" | "low";
  requires_auth: boolean;
}

export interface RoleSpec {
  name: string;
  description: string;
  is_admin: boolean;
}

export interface MonetizationSpec {
  model: string;
  tiers: string[];
  payment_provider: string | null;
}

export interface IntentSchema {
  app_name: string;
  app_type: AppType;
  core_entities: string[];
  features: FeatureSpec[];
  user_roles: RoleSpec[];
  monetization: MonetizationSpec | null;
  integrations: string[];
  ambiguities: string[];
  assumptions: string[];
  complexity_score: number;
}

export interface ClarificationRequest {
  needs_clarification: true;
  reason: string;
  questions: string[];
  partial_intent: IntentSchema | null;
}

// ── Architecture ─────────────────────────────────────────────────────────
export interface PageSpec {
  name: string;
  route: string;
  description: string;
  requires_auth: boolean;
  roles_allowed: string[];
  parent_page: string | null;
}

export interface APIGroupSpec {
  name: string;
  base_path: string;
  description: string;
  entity_ref: string;
}

export interface EntitySpec {
  name: string;
  description: string;
  relationships: string[];
  is_core: boolean;
}

export interface AuthStrategySpec {
  type: string;
  provider: string | null;
  token_expiry_hours: number;
  refresh_token: boolean;
  mfa_enabled: boolean;
}

export interface BusinessRule {
  id: string;
  description: string;
  applies_to: string[];
  condition: string;
  action: string;
}

export interface DataFlowEdge {
  from_node: string;
  to_node: string;
  description: string;
  data_type: string;
}

export interface ArchitectureSchema {
  pages: PageSpec[];
  api_groups: APIGroupSpec[];
  db_entities: EntitySpec[];
  auth_strategy: AuthStrategySpec;
  business_rules: BusinessRule[];
  data_flow: DataFlowEdge[];
}

// ── UI Schema ─────────────────────────────────────────────────────────────
export interface ValidationRule {
  rule: string;
  message: string;
}

export interface ComponentSpec {
  id: string;
  type: string;
  props: Record<string, unknown>;
  data_binding: string | null;
  validation_rules: ValidationRule[];
  conditional_visibility: string | null;
  children: ComponentSpec[];
}

export interface PageUISpec {
  page_name: string;
  route: string;
  title: string;
  layout: string;
  components: ComponentSpec[];
  requires_auth: boolean;
  roles_allowed: string[];
}

export interface UISchema {
  pages: PageUISpec[];
  navigation: Record<string, unknown>;
  theme: Record<string, unknown>;
}

// ── API Schema ────────────────────────────────────────────────────────────
export interface FieldSpec {
  name: string;
  type: string;
  required: boolean;
  validation: string | null;
  description: string;
}

export interface RequestBody {
  content_type: string;
  fields: FieldSpec[];
  example: Record<string, unknown>;
}

export interface ResponseBody {
  status_code: number;
  content_type: string;
  fields: FieldSpec[];
  is_list: boolean;
  example: Record<string, unknown>;
}

export interface EndpointSpec {
  id: string;
  path: string;
  method: HttpMethod;
  summary: string;
  description: string;
  request_body: RequestBody | null;
  response: ResponseBody;
  auth_required: boolean;
  roles_allowed: string[];
  db_entity_ref: string;
  tags: string[];
}

export interface APISchema {
  endpoints: EndpointSpec[];
  base_url: string;
  version: string;
  auth_header: string;
}

// ── DB Schema ─────────────────────────────────────────────────────────────
export interface FKReference {
  table: string;
  column: string;
  on_delete: string;
}

export interface ColumnSpec {
  name: string;
  type: string;
  nullable: boolean;
  default: unknown;
  is_pk: boolean;
  is_fk: boolean;
  references: FKReference | null;
  unique: boolean;
  index: boolean;
  description: string;
}

export interface IndexSpec {
  name: string;
  columns: string[];
  unique: boolean;
}

export interface TableSpec {
  name: string;
  description: string;
  columns: ColumnSpec[];
  indexes: IndexSpec[];
  primary_key: string;
}

export interface DBSchema {
  tables: TableSpec[];
  db_type: string;
  version: string;
}

// ── Auth Schema ───────────────────────────────────────────────────────────
export interface Permission {
  resource: string;
  actions: string[];
}

export interface RolePermissions {
  role: string;
  permissions: Permission[];
  inherits_from: string | null;
}

export interface PermissionMatrix {
  roles: RolePermissions[];
}

export interface ProtectedRoute {
  route: string;
  roles_allowed: string[];
  redirect_to: string;
}

export interface TokenConfig {
  algorithm: string;
  access_token_expiry_minutes: number;
  refresh_token_expiry_days: number;
  issuer: string;
}

export interface AuthSchema {
  strategy: string;
  roles: string[];
  permission_matrix: PermissionMatrix;
  protected_routes: ProtectedRoute[];
  token_config: TokenConfig;
  oauth_providers: string[];
  password_policy: Record<string, unknown>;
}

// ── Validation ────────────────────────────────────────────────────────────
export interface ValidationError {
  error_id: string;
  check_id: string;
  stage: string;
  layer: string;
  severity: ValidationSeverity;
  description: string;
  affected_paths: string[];
  suggested_fix: string;
  before_value: unknown;
  after_value: unknown;
  repair_iteration: number | null;
}

export interface CheckResult {
  check_id: string;
  name: string;
  description: string;
  passed: boolean;
  errors: ValidationError[];
}

export interface ValidationReport {
  checks_run: number;
  checks_passed: number;
  errors_found: number;
  errors_fixed: number;
  unfixed_errors: ValidationError[];
  repair_iterations: number;
  check_results: CheckResult[];
  all_errors: ValidationError[];
}

// ── Output ────────────────────────────────────────────────────────────────
export interface ExecutionPreview {
  table_count: number;
  endpoint_count: number;
  page_count: number;
  role_count: number;
  complexity: "low" | "medium" | "high";
}

export interface ModelUsage {
  model: string;
  tokens: number;
  cost_usd: number;
  latency_ms: number;
}

export interface GenerationMetadata {
  latency_ms: number;
  llm_calls: number;
  total_tokens: number;
  cost_usd: number;
  timestamp: string;
  model_usage: Record<string, ModelUsage>;
}

export interface AllSchemas {
  ui: UISchema | null;
  api: APISchema | null;
  db: DBSchema | null;
  auth: AuthSchema | null;
}

export interface CompilationResult {
  generation_id: string;
  status: GenerationStatus;
  prompt: string;
  intent: IntentSchema | null;
  clarification_needed: ClarificationRequest | null;
  architecture: ArchitectureSchema | null;
  schemas: AllSchemas;
  validation_report: ValidationReport;
  assumptions_made: string[];
  execution_preview: ExecutionPreview;
  metadata: GenerationMetadata;
  error_message: string | null;
}

// ── Pipeline Events ───────────────────────────────────────────────────────
export interface PipelineEvent {
  type: "progress" | "log" | "complete" | "error";
  stage?: string;
  status?: PipelineStatus;
  message?: string;
  elapsed_ms?: number;
  tokens_used?: number;
  timestamp?: number;
  level?: "info" | "success" | "warning" | "error";
  data?: unknown;
}

// ── History ───────────────────────────────────────────────────────────────
export interface GenerationSummary {
  id: string;
  prompt_preview: string;
  status: GenerationStatus;
  app_type: AppType;
  page_count: number;
  table_count: number;
  endpoint_count: number;
  role_count: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms: number;
  repair_iterations: number;
  created_at: string;
}

// ── Evaluation ────────────────────────────────────────────────────────────
export interface EvalResult {
  id: string;
  test_id: string;
  test_name: string;
  category: "normal" | "edge";
  status: string;
  score: number;
  repair_iterations: number;
  latency_ms: number;
  cost_usd: number;
  error_message: string;
  generation_id: string;
  created_at: string;
}

export interface EvalAggregate {
  total: number;
  success_rate: number;
  avg_latency_ms: number;
  avg_cost_usd: number;
  avg_score: number;
  avg_repair_iterations: number;
  results: EvalResult[];
}
