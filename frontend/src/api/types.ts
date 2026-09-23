export interface PatientRead {
  id: number;
  full_name: string;
  birth_year: number | null;
  diagnosis: string | null;
  diagnosis_date: string | null;
  stage: string | null;
  paraprotein_type: string | null;
  comorbidities: string[];
  allergies: string[];
  notes: string | null;
}

export type PatientUpdate = Partial<Omit<PatientRead, "id">>;

export interface LatestLabValue {
  code: string;
  name_ru: string;
  unit: string | null;
  value: number | null;
  value_text: string | null;
  taken_at: string;
  flag: "L" | "H" | "N" | null;
  change_pct: number | null;
  previous_value: number | null;
}

export interface LabSeriesPoint {
  taken_at: string;
  value: number | null;
  value_text: string | null;
  flag: "L" | "H" | "N" | null;
}

export interface LabSeries {
  code: string;
  name_ru: string;
  unit: string | null;
  points: LabSeriesPoint[];
}

export interface DocumentRead {
  id: number;
  kind: "lab" | "discharge" | "imaging" | "other";
  mime: string;
  taken_at: string | null;
  lab_name: string | null;
  status: "uploaded" | "parsing" | "needs_review" | "confirmed" | "failed";
  created_at: string;
}

export interface LabResultRead {
  id: number;
  analyte_code: string;
  analyte_name: string;
  value: number | null;
  value_text: string | null;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  flag: "L" | "H" | "N" | null;
  confirmed: boolean;
}

export interface VisitRead {
  id: number;
  date: string;
  doctor: string | null;
  clinic: string | null;
  summary: string | null;
  decisions: string | null;
  next_visit_date: string | null;
}

export type VisitCreate = Omit<VisitRead, "id">;

export interface TreatmentRead {
  id: number;
  regimen: string;
  cycle_no: number | null;
  start_date: string;
  end_date: string | null;
  notes: string | null;
}

export type TreatmentCreate = Omit<TreatmentRead, "id">;
