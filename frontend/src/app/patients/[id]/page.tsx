"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import { Card, Button, Badge } from "@/components/ui/primitives";
import {
  ArrowLeft,
  User,
  Phone,
  Mail,
  MapPin,
  Calendar,
  UserCheck,
  ClipboardList,
  AlertCircle,
  FileText
} from "lucide-react";

interface Patient {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone: string;
  email: string | null;
  address: { street?: string; city?: string } | null;
  referring_provider: string | null;
  communication_preference: string;
  consent_operational: boolean;
  consent_promotional: boolean;
  created_at: string;
}

interface PatientOrderSummary {
  id: number;
  order_number: string;
  status: string;
  payment_status: string;
  total_amount: string;
  created_at: string;
  items: { test_name_snapshot: string; test_code_snapshot: string }[];
}

export default function PatientProfilePage() {
  const params = useParams();
  const router = useRouter();
  const patientId = params.id;

  const [patient, setPatient] = useState<Patient | null>(null);
  const [patientOrders, setPatientOrders] = useState<PatientOrderSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPatientDetails = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [patData, ordersData] = await Promise.all([
          api.get<Patient>(`/patients/${patientId}`),
          api.get<PatientOrderSummary[]>(`/orders/patient/${patientId}`).catch(() => [])
        ]);
        setPatient(patData);
        setPatientOrders(ordersData);
      } catch (err: any) {
        setError(err.detail || "Failed to load patient profile.");
      } finally {
        setIsLoading(false);
      }
    };

    if (patientId) {
      fetchPatientDetails();
    }
  }, [patientId]);

  const calculateAge = (dobString: string) => {
    const today = new Date();
    const birthDate = new Date(dobString);
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 w-full">
        <div className="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs text-slate-500 font-semibold mt-4">Loading patient profile...</span>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center select-none max-w-md mx-auto w-full px-4">
        <div className="w-16 h-16 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center mb-6 border border-rose-100/50">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h2 className="text-lg font-black text-slate-900 tracking-tight">Record Not Found</h2>
        <p className="text-sm text-slate-500 font-medium mt-2 leading-relaxed">
          {error || "We could not find the patient record. It may belong to another organization."}
        </p>
        <Button
          variant="secondary"
          onClick={() => router.push("/patients")}
          className="mt-6 font-bold shadow-sm"
        >
          Return to Patient Registry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Return button & header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/patients")}
          className="p-2 hover:bg-slate-100 rounded-lg text-slate-500 hover:text-slate-900 border border-slate-200/80 bg-white transition-all shadow-sm"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <span className="block text-[10px] text-teal-600 font-black uppercase tracking-wider">
            Clinical Patient File
          </span>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight mt-0.5">
            {patient.first_name} {patient.last_name}
          </h1>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Side: Demographic profile card */}
        <Card className="lg:col-span-1 p-6 border border-slate-200/80 shadow-sm flex flex-col gap-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200/80 flex items-center justify-center font-bold text-slate-700 text-lg">
              {patient.first_name.charAt(0)}
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-black text-slate-400">Patient ID</span>
              <span className="text-sm font-black text-slate-800 tracking-tight mt-0.5">
                {patient.patient_id}
              </span>
            </div>
          </div>

          <hr className="border-slate-100" />

          {/* Core Info */}
          <div className="flex flex-col gap-3.5">
            <div className="flex items-center gap-3">
              <Calendar className="w-4 h-4 text-slate-400" />
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-400 font-bold uppercase">Age / Gender</span>
                <span className="text-xs font-semibold text-slate-800 capitalize mt-0.5">
                  {calculateAge(patient.date_of_birth)} years ({patient.gender})
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Phone className="w-4 h-4 text-slate-400" />
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-400 font-bold uppercase">Mobile Phone</span>
                <span className="text-xs font-semibold text-slate-800 mt-0.5">{patient.phone}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Mail className="w-4 h-4 text-slate-400" />
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-400 font-bold uppercase">Email Address</span>
                <span className="text-xs font-semibold text-slate-800 mt-0.5">
                  {patient.email || "No email registered"}
                </span>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPin className="w-4 h-4 text-slate-400 mt-0.5" />
              <div className="flex flex-col">
                <span className="text-[10px] text-slate-400 font-bold uppercase">Home Address</span>
                <span className="text-xs font-semibold text-slate-800 mt-0.5 leading-relaxed">
                  {patient.address
                    ? `${patient.address.street || ""}, ${patient.address.city || ""}`
                    : "No address registered"}
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* Right Side: Detail Blocks & Laboratory history list */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Referral Provider and Consent blocks */}
          <Card className="p-6 border border-slate-200/80 shadow-sm grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex flex-col gap-4">
              <span className="text-xs font-black text-slate-800 border-b border-slate-100 pb-2">
                Referring Doctor
              </span>
              <div className="flex items-center gap-3">
                <UserCheck className="w-5 h-5 text-slate-400" />
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-bold uppercase">Doctor Code / Name</span>
                  <span className="text-sm font-bold text-slate-800 mt-0.5">
                    {patient.referring_provider || "Self-referred"}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-4">
              <span className="text-xs font-black text-slate-800 border-b border-slate-100 pb-2">
                Preferences & Consents
              </span>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                  <span>Channel Preference:</span>
                  <span className="capitalize font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-100">
                    {patient.communication_preference}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                  <span>Operational Alerts:</span>
                  <span className={`font-bold ${patient.consent_operational ? "text-emerald-600" : "text-rose-600"}`}>
                    {patient.consent_operational ? "Granted" : "Denied"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
                  <span>Promotional alerts:</span>
                  <span className={`font-bold ${patient.consent_promotional ? "text-emerald-600" : "text-slate-400"}`}>
                    {patient.consent_promotional ? "Granted" : "Denied"}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Laboratory Visits History Grid */}
          <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-black text-slate-800 uppercase tracking-wider">Laboratory Orders & History</span>
              </div>
              <Button
                variant="primary"
                size="sm"
                className="bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs h-8 px-3"
                onClick={() => router.push(`/orders/new?patient_id=${patient.id}`)}
              >
                + New Order
              </Button>
            </div>
            
            {/* Orders list or empty state */}
            {patientOrders.length === 0 ? (
              <div className="flex flex-col items-center justify-center text-center p-12 py-12">
                <div className="w-12 h-12 rounded-xl bg-slate-50 text-slate-400 flex items-center justify-center mb-4 border border-slate-100">
                  <FileText className="w-6 h-6" />
                </div>
                <h3 className="text-xs font-bold text-slate-800">No laboratory orders yet.</h3>
                <p className="text-[11px] text-slate-500 font-semibold max-w-xs mt-1 leading-relaxed">
                  Click "+ New Order" above to book laboratory tests for this patient.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {patientOrders.map((ord) => (
                  <div key={ord.id} className="p-4 hover:bg-slate-50/80 transition-colors flex items-center justify-between gap-4">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-black text-slate-900">{ord.order_number}</span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          ord.status === "Pending" ? "bg-amber-100 text-amber-800 border border-amber-200" :
                          ord.status === "Published" ? "bg-emerald-100 text-emerald-800 border border-emerald-200" :
                          ord.status === "Cancelled" ? "bg-rose-100 text-rose-800 border border-rose-200" :
                          "bg-blue-100 text-blue-800 border border-blue-200"
                        }`}>
                          {ord.status}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600 font-medium">
                        {ord.items.map(i => i.test_name_snapshot).join(" + ")}
                      </div>
                      <div className="text-[11px] text-slate-400 font-semibold">
                        {new Date(ord.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-sm font-extrabold text-slate-900">₹{parseFloat(ord.total_amount).toFixed(2)}</div>
                        <span className={`inline-block text-[10px] font-bold ${
                          ord.payment_status === "Paid" ? "text-emerald-600" :
                          ord.payment_status === "Partial" ? "text-orange-600" : "text-amber-600"
                        }`}>
                          Payment: {ord.payment_status}
                        </span>
                      </div>
                      <Button
                        variant="secondary"
                        size="sm"
                        className="h-8 px-3 text-xs font-bold border-slate-200 hover:bg-slate-100"
                        onClick={() => router.push(`/orders/${ord.id}`)}
                      >
                        View Order
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
