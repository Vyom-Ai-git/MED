"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Card, Badge, Button, Input, Select, Table, Modal, Toast } from "@/components/ui/primitives";
import {
  Calendar,
  Plus,
  Stethoscope,
  Truck,
  RefreshCw,
  Search,
} from "lucide-react";

interface PatientResult {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  phone: string;
}

interface DoctorResult {
  id: number;
  name: string;
  specialty: string;
  consultation_fee: number;
}

interface BookingItem {
  kind: "doctor" | "lab";
  id: number;
  booking_number: string;
  patient_name: string;
  patient_phone?: string;
  doctor_name?: string;
  doctor_specialty?: string;
  booking_type?: string;
  branch_name?: string;
  date: string;
  start_time?: string;
  end_time?: string;
  preferred_slot?: string;
  consultation_type?: string;
  status: string;
  fee?: number;
  tests_requested?: string[];
  notes?: string;
}

const DOCTOR_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"];
const LAB_STATUSES = ["Pending", "Confirmed", "Collected", "Completed", "Cancelled"];

function usePatientSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PatientResult[]>([]);
  const [selected, setSelected] = useState<PatientResult | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (!query || selected) {
      setResults([]);
      return;
    }
    timer.current = setTimeout(async () => {
      try {
        const data = await api.get<{ items: PatientResult[] }>(
          `/patients?q=${encodeURIComponent(query)}&page_size=6`
        );
        setResults(data.items || []);
      } catch {
        setResults([]);
      }
    }, 300);
  }, [query, selected]);

  return { query, setQuery, results, selected, setSelected };
}

function PatientPicker({
  patient,
}: {
  patient: ReturnType<typeof usePatientSearch>;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-slate-700">Patient</label>
      {patient.selected ? (
        <div className="flex items-center justify-between px-3.5 py-2.5 rounded-lg border border-teal-200 bg-teal-50/50">
          <span className="text-sm font-bold text-slate-900">
            {patient.selected.first_name} {patient.selected.last_name}{" "}
            <span className="text-xs font-mono text-teal-700">({patient.selected.patient_id})</span>
          </span>
          <button
            className="text-xs font-bold text-slate-500 hover:text-rose-600"
            onClick={() => {
              patient.setSelected(null);
              patient.setQuery("");
            }}
          >
            Change
          </button>
        </div>
      ) : (
        <div className="relative">
          <Input
            icon={<Search className="w-4 h-4" />}
            placeholder="Search by name, ID, or phone…"
            value={patient.query}
            onChange={(e) => patient.setQuery(e.target.value)}
          />
          {patient.results.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
              {patient.results.map((p) => (
                <button
                  key={p.id}
                  className="w-full text-left px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 border-b border-slate-50 last:border-0"
                  onClick={() => {
                    patient.setSelected(p);
                    patient.setQuery("");
                  }}
                >
                  {p.first_name} {p.last_name} · {p.patient_id} · {p.phone}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AppointmentsPage() {
  const [tab, setTab] = useState<"doctor" | "lab">("doctor");
  const [items, setItems] = useState<BookingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Doctor booking form state
  const doctorPatient = usePatientSearch();
  const [doctors, setDoctors] = useState<DoctorResult[]>([]);
  const [doctorId, setDoctorId] = useState<string>("");
  const [apptDate, setApptDate] = useState("");
  const [startTime, setStartTime] = useState("10:00");
  const [endTime, setEndTime] = useState("10:30");
  const [consultType, setConsultType] = useState("in_person");

  // Lab booking form state
  const labPatient = usePatientSearch();
  const [bookingType, setBookingType] = useState("home_collection");
  const [preferredDate, setPreferredDate] = useState("");
  const [preferredSlot, setPreferredSlot] = useState("08:00 AM - 10:00 AM");
  const [testsRequested, setTestsRequested] = useState("");

  const loadBookings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<{ items: BookingItem[] }>(`/bookings?booking_kind=${tab}`);
      setItems(data.items || []);
    } catch (err: any) {
      setError(err.detail || err.message || "Failed to load appointments");
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    loadBookings();
  }, [loadBookings]);

  useEffect(() => {
    if (modalOpen && tab === "doctor" && doctors.length === 0) {
      api.get<{ items: DoctorResult[] }>("/doctors").then((d) => setDoctors(d.items || []));
    }
  }, [modalOpen, tab, doctors.length]);

  const resetForms = () => {
    doctorPatient.setSelected(null);
    doctorPatient.setQuery("");
    labPatient.setSelected(null);
    labPatient.setQuery("");
    setDoctorId("");
    setApptDate("");
    setPreferredDate("");
    setTestsRequested("");
  };

  const handleCreate = async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (tab === "doctor") {
        if (!doctorPatient.selected || !doctorId || !apptDate) {
          setError("Please select a patient, doctor, and date.");
          setSubmitting(false);
          return;
        }
        await api.post("/bookings/doctor", {
          patient_id: doctorPatient.selected.id,
          doctor_id: Number(doctorId),
          appointment_date: apptDate,
          start_time: startTime,
          end_time: endTime,
          consultation_type: consultType,
        });
      } else {
        if (!labPatient.selected || !preferredDate) {
          setError("Please select a patient and preferred date.");
          setSubmitting(false);
          return;
        }
        await api.post("/bookings/lab", {
          patient_id: labPatient.selected.id,
          booking_type: bookingType,
          preferred_date: preferredDate,
          preferred_slot: preferredSlot,
          tests_requested: testsRequested
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        });
      }
      setModalOpen(false);
      resetForms();
      loadBookings();
    } catch (err: any) {
      setError(err.detail || err.message || "Failed to create booking");
    } finally {
      setSubmitting(false);
    }
  };

  const updateStatus = async (item: BookingItem, newStatus: string) => {
    try {
      await api.patch(`/bookings/${item.kind}/${item.id}/status?status=${encodeURIComponent(newStatus)}`, {});
      loadBookings();
    } catch (err: any) {
      setError(err.detail || err.message || "Failed to update status");
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <Calendar className="w-6 h-6 text-teal-600" /> Appointments
          </h1>
          <p className="text-xs font-semibold text-slate-500 mt-0.5">
            Doctor consultations and home / walk-in sample collection bookings
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={loadBookings}>
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
          <Button variant="primary" onClick={() => setModalOpen(true)} className="bg-teal-600 hover:bg-teal-700 font-bold">
            <Plus className="w-4 h-4 mr-2" /> New Booking
          </Button>
        </div>
      </div>

      {error && <Toast type="error" message={error} onClose={() => setError(null)} />}

      <div className="flex gap-2">
        <button
          onClick={() => setTab("doctor")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold border transition-all ${
            tab === "doctor"
              ? "bg-teal-50 text-teal-700 border-teal-200"
              : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <Stethoscope className="w-3.5 h-3.5" /> Doctor Consultations
        </button>
        <button
          onClick={() => setTab("lab")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold border transition-all ${
            tab === "lab"
              ? "bg-teal-50 text-teal-700 border-teal-200"
              : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50"
          }`}
        >
          <Truck className="w-3.5 h-3.5" /> Home / Walk-in Collection
        </button>
      </div>

      <Card>
        {tab === "doctor" ? (
          <Table<BookingItem>
            isLoading={loading}
            data={items}
            emptyMessage="No doctor appointments booked yet."
            columns={[
              { header: "Booking #", accessor: (r) => <span className="font-mono text-xs font-bold">{r.booking_number}</span> },
              { header: "Patient", accessor: (r) => r.patient_name },
              { header: "Doctor", accessor: (r) => `${r.doctor_name} (${r.doctor_specialty || "—"})` },
              { header: "Date / Time", accessor: (r) => `${r.date} · ${r.start_time}-${r.end_time}` },
              { header: "Type", accessor: (r) => r.consultation_type },
              { header: "Status", accessor: (r) => <Badge status={r.status} /> },
              {
                header: "Update",
                accessor: (r) => (
                  <select
                    className="text-xs font-semibold border border-slate-200 rounded-lg px-2 py-1"
                    value={r.status}
                    onChange={(e) => updateStatus(r, e.target.value)}
                  >
                    {DOCTOR_STATUSES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                ),
              },
            ]}
          />
        ) : (
          <Table<BookingItem>
            isLoading={loading}
            data={items}
            emptyMessage="No lab collection bookings yet."
            columns={[
              { header: "Booking #", accessor: (r) => <span className="font-mono text-xs font-bold">{r.booking_number}</span> },
              { header: "Patient", accessor: (r) => r.patient_name },
              { header: "Type", accessor: (r) => r.booking_type },
              { header: "Date / Slot", accessor: (r) => `${r.date} · ${r.preferred_slot}` },
              { header: "Tests", accessor: (r) => (r.tests_requested || []).join(", ") || "—" },
              { header: "Status", accessor: (r) => <Badge status={r.status} /> },
              {
                header: "Update",
                accessor: (r) => (
                  <select
                    className="text-xs font-semibold border border-slate-200 rounded-lg px-2 py-1"
                    value={r.status}
                    onChange={(e) => updateStatus(r, e.target.value)}
                  >
                    {LAB_STATUSES.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                ),
              },
            ]}
          />
        )}
      </Card>

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={tab === "doctor" ? "New Doctor Appointment" : "New Collection Booking"}
        actions={
          <>
            <Button variant="outline" onClick={() => setModalOpen(false)}>Cancel</Button>
            <Button variant="primary" isLoading={submitting} onClick={handleCreate} className="bg-teal-600 hover:bg-teal-700">
              Create Booking
            </Button>
          </>
        }
      >
        {tab === "doctor" ? (
          <div className="flex flex-col gap-4">
            <PatientPicker patient={doctorPatient} />
            <Select
              label="Doctor"
              value={doctorId}
              onChange={(e) => setDoctorId(e.target.value)}
              options={[{ value: "", label: "Select a doctor…" }, ...doctors.map((d) => ({ value: d.id, label: `${d.name} — ${d.specialty}` }))]}
            />
            <div className="grid grid-cols-3 gap-3">
              <Input label="Date" type="date" value={apptDate} onChange={(e) => setApptDate(e.target.value)} />
              <Input label="Start" type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
              <Input label="End" type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
            </div>
            <Select
              label="Consultation Type"
              value={consultType}
              onChange={(e) => setConsultType(e.target.value)}
              options={[
                { value: "in_person", label: "In-Person" },
                { value: "tele_consult", label: "Tele-Consult" },
              ]}
            />
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <PatientPicker patient={labPatient} />
            <Select
              label="Booking Type"
              value={bookingType}
              onChange={(e) => setBookingType(e.target.value)}
              options={[
                { value: "home_collection", label: "Home Collection" },
                { value: "walk_in", label: "Walk-In" },
              ]}
            />
            <div className="grid grid-cols-2 gap-3">
              <Input label="Preferred Date" type="date" value={preferredDate} onChange={(e) => setPreferredDate(e.target.value)} />
              <Input label="Preferred Slot" placeholder="08:00 AM - 10:00 AM" value={preferredSlot} onChange={(e) => setPreferredSlot(e.target.value)} />
            </div>
            <Input
              label="Tests Requested (comma-separated)"
              placeholder="CBC, Lipid Profile, TSH"
              value={testsRequested}
              onChange={(e) => setTestsRequested(e.target.value)}
            />
          </div>
        )}
      </Modal>
    </div>
  );
}
