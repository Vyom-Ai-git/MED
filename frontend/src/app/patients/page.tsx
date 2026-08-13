"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import {
  Table,
  Button,
  Card,
  Modal,
  Input,
  Select,
  Toast,
  Badge
} from "@/components/ui/primitives";
import {
  UserPlus,
  Search,
  Phone,
  Mail,
  Calendar,
  AlertCircle,
  Eye,
  Edit3,
  MapPin,
  CheckCircle,
  AlertTriangle
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

interface PaginatedResponse {
  items: Patient[];
  total: number;
  page: number;
  page_size: number;
}

export default function PatientsPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [patients, setPatients] = useState<Patient[]>([]);
  const [totalPatients, setTotalPatients] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Success and Error Toasts
  const [toastSuccess, setToastSuccess] = useState<string | null>(null);
  const [toastError, setToastError] = useState<string | null>(null);

  // Registration Modal States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [dob, setDob] = useState("");
  const [gender, setGender] = useState("male");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [street, setStreet] = useState("");
  const [city, setCity] = useState("");
  const [referringProvider, setReferringProvider] = useState("");
  const [commPreference, setCommPreference] = useState("email");
  const [consentOperational, setConsentOperational] = useState(true);
  const [consentPromotional, setConsentPromotional] = useState(false);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Duplicate Warning Modal States
  const [duplicateWarningOpen, setDuplicateWarningOpen] = useState(false);
  const [duplicateId, setDuplicateId] = useState<number | null>(null);

  // Edit Modal States
  const [activeEditPatient, setActiveEditPatient] = useState<Patient | null>(null);
  const [editFirstName, setEditFirstName] = useState("");
  const [editLastName, setEditLastName] = useState("");
  const [editDob, setEditDob] = useState("");
  const [editGender, setEditGender] = useState("male");
  const [editPhone, setEditPhone] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editStreet, setEditStreet] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editReferringProvider, setEditReferringProvider] = useState("");
  const [editCommPreference, setEditCommPreference] = useState("email");
  const [editConsentOperational, setEditConsentOperational] = useState(true);
  const [editConsentPromotional, setEditConsentPromotional] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editFormError, setEditFormError] = useState<string | null>(null);

  const fetchPatients = async (page = 1, query = "") => {
    setIsLoading(true);
    setError(null);
    try {
      const url = `/patients?page=${page}&page_size=${pageSize}` + 
                  (query ? `&q=${encodeURIComponent(query)}` : "");
      const res = await api.get<PaginatedResponse>(url);
      setPatients(res.items);
      setTotalPatients(res.total);
      setCurrentPage(res.page);
    } catch (err: any) {
      setError(err.detail || "Failed to load patient records.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients(1, searchQuery);
  }, [searchQuery]);

  const handleRegisterPatient = async (e?: React.FormEvent, forceBypass = false) => {
    if (e) e.preventDefault();

    if (!firstName || !lastName || !dob || !phone) {
      setFormError("Please fill in all required fields.");
      return;
    }

    // Check that DOB is not in the future
    const selectedDate = new Date(dob);
    const today = new Date();
    if (selectedDate > today) {
      setFormError("Date of Birth cannot be in the future.");
      return;
    }

    setFormError(null);
    setIsSubmitting(true);
    try {
      const payload = {
        first_name: firstName,
        last_name: lastName,
        date_of_birth: dob,
        gender,
        phone,
        email: email || null,
        address: street || city ? { street, city } : null,
        referring_provider: referringProvider || "Self",
        communication_preference: commPreference,
        consent_operational: consentOperational,
        consent_promotional: consentPromotional,
        organization_id: user?.organization_id,
        ignore_duplicate: forceBypass
      };

      await api.post("/patients", payload);
      setToastSuccess("Patient successfully registered!");
      setIsModalOpen(false);
      setDuplicateWarningOpen(false);
      
      // Reset form fields
      setFirstName("");
      setLastName("");
      setDob("");
      setGender("male");
      setPhone("");
      setEmail("");
      setStreet("");
      setCity("");
      setReferringProvider("");
      setCommPreference("email");
      setConsentOperational(true);
      setConsentPromotional(false);

      fetchPatients(1, searchQuery);
    } catch (err: any) {
      if (err.status === 409 && err.detail?.existing_id) {
        // Likely duplicate patient warning trigger
        setDuplicateId(err.detail.existing_id);
        setDuplicateWarningOpen(true);
      } else {
        setFormError(err.detail || "Failed to register patient. Please check inputs.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeEditPatient) return;

    if (!editFirstName || !editLastName || !editDob || !editPhone) {
      setEditFormError("Please fill in all required fields.");
      return;
    }

    // Check DOB
    const selectedDate = new Date(editDob);
    const today = new Date();
    if (selectedDate > today) {
      setEditFormError("Date of Birth cannot be in the future.");
      return;
    }

    setEditFormError(null);
    setIsEditing(true);
    try {
      const payload = {
        first_name: editFirstName,
        last_name: editLastName,
        date_of_birth: editDob,
        gender: editGender,
        phone: editPhone,
        email: editEmail || null,
        address: editStreet || editCity ? { street: editStreet, city: editCity } : null,
        referring_provider: editReferringProvider || "Self",
        communication_preference: editCommPreference,
        consent_operational: editConsentOperational,
        consent_promotional: editConsentPromotional
      };

      await api.patch(`/patients/${activeEditPatient.id}`, payload);
      setToastSuccess("Patient profile updated successfully!");
      setActiveEditPatient(null);

      fetchPatients(currentPage, searchQuery);
    } catch (err: any) {
      setEditFormError(err.detail || "Failed to update patient profile.");
    } finally {
      setIsEditing(false);
    }
  };

  const openEditModal = (pat: Patient) => {
    setActiveEditPatient(pat);
    setEditFirstName(pat.first_name);
    setEditLastName(pat.last_name);
    setEditDob(pat.date_of_birth);
    setEditGender(pat.gender);
    setEditPhone(pat.phone);
    setEditEmail(pat.email || "");
    setEditStreet(pat.address?.street || "");
    setEditCity(pat.address?.city || "");
    setEditReferringProvider(pat.referring_provider || "");
    setEditCommPreference(pat.communication_preference);
    setEditConsentOperational(pat.consent_operational);
    setEditConsentPromotional(pat.consent_promotional);
  };

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

  const columns = [
    {
      header: "Patient ID",
      accessor: (row: Patient) => (
        <span className="font-bold text-slate-800 tracking-tight">{row.patient_id}</span>
      ),
    },
    {
      header: "Patient Name",
      accessor: (row: Patient) => (
        <div className="flex flex-col">
          <span className="font-bold text-slate-900">{`${row.first_name} ${row.last_name}`}</span>
          {row.email && <span className="text-[10px] text-slate-400">{row.email}</span>}
        </div>
      ),
    },
    {
      header: "Demographics",
      accessor: (row: Patient) => (
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 capitalize">
          <span>{calculateAge(row.date_of_birth)} yrs</span>
          <span className="text-slate-300">•</span>
          <span>{row.gender}</span>
        </div>
      ),
    },
    {
      header: "Phone",
      accessor: (row: Patient) => (
        <span className="flex items-center gap-1.5 text-xs text-slate-600 font-semibold">
          <Phone className="w-3.5 h-3.5 text-slate-400" />
          {row.phone}
        </span>
      ),
    },
    {
      header: "Referring Provider",
      accessor: (row: Patient) => (
        <span className="text-xs text-slate-500 font-semibold">{row.referring_provider || "Self"}</span>
      ),
    },
    {
      header: "Consent",
      accessor: (row: Patient) => (
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] flex items-center gap-1 font-bold text-slate-500">
            <CheckCircle className={`w-3 h-3 ${row.consent_operational ? "text-emerald-500" : "text-slate-300"}`} />
            Operational
          </span>
          <span className="text-[10px] flex items-center gap-1 font-bold text-slate-500">
            <CheckCircle className={`w-3 h-3 ${row.consent_promotional ? "text-emerald-500" : "text-slate-300"}`} />
            Promotional
          </span>
        </div>
      ),
    },
    {
      header: "Actions",
      accessor: (row: Patient) => {
        const canWrite = user?.role === "admin" || user?.role === "reception";
        return (
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push(`/patients/${row.id}`)}
              className="p-1.5 hover:bg-slate-100 rounded text-slate-500 hover:text-teal-600 transition-colors"
              title="View Profile & History"
            >
              <Eye className="w-4 h-4" />
            </button>
            {canWrite && (
              <button
                onClick={() => openEditModal(row)}
                className="p-1.5 hover:bg-slate-100 rounded text-slate-500 hover:text-teal-600 transition-colors"
                title="Edit Demographics"
              >
                <Edit3 className="w-4 h-4" />
              </button>
            )}
          </div>
        );
      },
    },
  ];

  const totalPages = Math.ceil(totalPatients / pageSize);
  const isReceptionOrAdmin = user?.role === "admin" || user?.role === "reception";

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Top action header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">Patient Registry</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Browse and manage registered patients, retrieve historical lab profiles, or enroll new entries.
          </p>
        </div>
        {isReceptionOrAdmin && (
          <Button
            variant="primary"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 text-xs font-bold py-2.5 px-4 shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            <span>Register Patient</span>
          </Button>
        )}
      </div>

      {/* Toast Notifications */}
      {toastSuccess && (
        <Toast type="success" text={toastSuccess} onClose={() => setToastSuccess(null)} />
      )}
      {toastError && (
        <Toast type="error" text={toastError} onClose={() => setToastError(null)} />
      )}

      {/* Search Bar & Registry Table */}
      <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
        <div className="p-5 border-b border-slate-100 bg-slate-50/20">
          <div className="max-w-md">
            <Input
              type="text"
              placeholder="Search by name, patient ID, phone..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              icon={<Search className="w-4 h-4 text-slate-400" />}
            />
          </div>
        </div>

        <Table
          columns={columns}
          data={patients}
          isLoading={isLoading}
          emptyMessage="No patients match your query. Register your first patient to begin laboratory operations."
        />

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-4 border-t border-slate-100 bg-slate-50/10">
            <span className="text-xs text-slate-500 font-semibold">
              Showing page {currentPage} of {totalPages} ({totalPatients} total records)
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => fetchPatients(currentPage - 1, searchQuery)}
                disabled={currentPage === 1 || isLoading}
                className="py-1.5 px-3 text-xs"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                onClick={() => fetchPatients(currentPage + 1, searchQuery)}
                disabled={currentPage === totalPages || isLoading}
                className="py-1.5 px-3 text-xs"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Register Patient Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register New Patient"
        actions={
          <>
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" form="register-patient-form" isLoading={isSubmitting}>
              Register Record
            </Button>
          </>
        }
      >
        <form id="register-patient-form" onSubmit={(e) => handleRegisterPatient(e, false)} className="flex flex-col gap-4">
          <div className="text-slate-900 font-black text-sm border-b border-slate-100 pb-2">
            Personal Information
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="First Name *"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="e.g. Jane"
              required
            />
            <Input
              label="Last Name *"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="e.g. Doe"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Date of Birth *"
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              required
            />
            <Select
              label="Gender *"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              options={[
                { value: "male", label: "Male" },
                { value: "female", label: "Female" },
                { value: "other", label: "Other" }
              ]}
            />
          </div>

          <div className="text-slate-900 font-black text-sm border-b border-slate-100 pt-2 pb-2">
            Contact & Location Details
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Mobile Phone *"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="e.g. +91 99999 88888"
              required
            />
            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. jane.doe@example.com"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Street Address"
              value={street}
              onChange={(e) => setStreet(e.target.value)}
              placeholder="e.g. Apt 4B, Sector 7"
            />
            <Input
              label="City"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="e.g. Bengaluru"
            />
          </div>

          <div className="text-slate-900 font-black text-sm border-b border-slate-100 pt-2 pb-2">
            Referral & Communication Preferences
          </div>
          <Input
            label="Referring Doctor / Provider"
            value={referringProvider}
            onChange={(e) => setReferringProvider(e.target.value)}
            placeholder="e.g. Dr. Verma or Self"
          />

          <Select
            label="Communication Channel"
            value={commPreference}
            onChange={(e) => setCommPreference(e.target.value)}
            options={[
              { value: "email", label: "Email Notifications" },
              { value: "whatsapp", label: "WhatsApp Alerts" },
              { value: "sms", label: "SMS Texts" }
            ]}
          />

          <div className="flex flex-col gap-2 bg-slate-50 p-4 rounded-lg border border-slate-100 mt-2">
            <label className="text-xs font-black text-slate-800">Patient Consent Declarations</label>
            <div className="flex items-start gap-3.5 mt-2">
              <input
                id="consent-operational"
                type="checkbox"
                checked={consentOperational}
                onChange={(e) => setConsentOperational(e.target.checked)}
                className="w-4 h-4 text-teal-600 border-slate-300 rounded focus:ring-teal-500 mt-0.5"
              />
              <div className="flex flex-col">
                <label htmlFor="consent-operational" className="text-xs font-bold text-slate-800">
                  Operational Communication Consent *
                </label>
                <span className="text-[10px] text-slate-500 font-semibold leading-relaxed mt-0.5">
                  Allows sending invoice details, critical reports, and medical notifications.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-3.5 mt-2">
              <input
                id="consent-promotional"
                type="checkbox"
                checked={consentPromotional}
                onChange={(e) => setConsentPromotional(e.target.checked)}
                className="w-4 h-4 text-teal-600 border-slate-300 rounded focus:ring-teal-500 mt-0.5"
              />
              <div className="flex flex-col">
                <label htmlFor="consent-promotional" className="text-xs font-bold text-slate-800">
                  Promotional / Marketing Consent
                </label>
                <span className="text-[10px] text-slate-500 font-semibold leading-relaxed mt-0.5">
                  Allows sharing laboratory checkup packages, campaigns, and news.
                </span>
              </div>
            </div>
          </div>

          {formError && (
            <div className="mt-2">
              <Toast type="error" text={formError} onClose={() => setFormError(null)} />
            </div>
          )}
        </form>
      </Modal>

      {/* Duplicate Patient Warning Confirmation Modal */}
      <Modal
        isOpen={duplicateWarningOpen}
        onClose={() => setDuplicateWarningOpen(false)}
        title="Possible Existing Patient"
        actions={
          <>
            <Button variant="outline" onClick={() => setDuplicateWarningOpen(false)}>
              Cancel
            </Button>
            {duplicateId && (
              <Button variant="secondary" onClick={() => {
                setDuplicateWarningOpen(false);
                setIsModalOpen(false);
                router.push(`/patients/${duplicateId}`);
              }} className="flex items-center gap-2">
                <Eye className="w-3.5 h-3.5" />
                <span>View Existing Patient</span>
              </Button>
            )}
            <Button
              variant="primary"
              onClick={() => handleRegisterPatient(undefined, true)}
              isLoading={isSubmitting}
            >
              Continue Registration
            </Button>
          </>
        }
      >
        <div className="flex flex-col items-center text-center p-4">
          <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-500 flex items-center justify-center mb-4 border border-amber-100">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-slate-900 text-sm">Duplicate Patient Match Detected</h3>
          <p className="text-xs text-slate-500 font-semibold leading-relaxed mt-2 max-w-sm">
            A patient with similar name, date of birth, and phone number already exists in your registry. 
            Would you like to review the existing file or bypass warning and register a new record?
          </p>
        </div>
      </Modal>

      {/* Edit Patient Modal */}
      {activeEditPatient && (
        <Modal
          isOpen={true}
          onClose={() => setActiveEditPatient(null)}
          title={`Edit Patient: ${activeEditPatient.first_name} ${activeEditPatient.last_name}`}
          actions={
            <>
              <Button variant="outline" onClick={() => setActiveEditPatient(null)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" form="edit-patient-form" isLoading={isEditing}>
                Update Profile
              </Button>
            </>
          }
        >
          <form id="edit-patient-form" onSubmit={handleUpdatePatient} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="First Name *"
                value={editFirstName}
                onChange={(e) => setEditFirstName(e.target.value)}
                placeholder="e.g. Jane"
                required
              />
              <Input
                label="Last Name *"
                value={editLastName}
                onChange={(e) => setEditLastName(e.target.value)}
                placeholder="e.g. Doe"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Date of Birth *"
                type="date"
                value={editDob}
                onChange={(e) => setEditDob(e.target.value)}
                required
              />
              <Select
                label="Gender *"
                value={editGender}
                onChange={(e) => setEditGender(e.target.value)}
                options={[
                  { value: "male", label: "Male" },
                  { value: "female", label: "Female" },
                  { value: "other", label: "Other" }
                ]}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Mobile Phone *"
                type="tel"
                value={editPhone}
                onChange={(e) => setEditPhone(e.target.value)}
                placeholder="e.g. +91 99999 88888"
                required
              />
              <Input
                label="Email Address"
                type="email"
                value={editEmail}
                onChange={(e) => setEditEmail(e.target.value)}
                placeholder="e.g. jane.doe@example.com"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Street Address"
                value={editStreet}
                onChange={(e) => setEditStreet(e.target.value)}
                placeholder="e.g. Apt 4B, Sector 7"
              />
              <Input
                label="City"
                value={editCity}
                onChange={(e) => setEditCity(e.target.value)}
                placeholder="e.g. Bengaluru"
              />
            </div>

            <Input
              label="Referring Doctor / Provider"
              value={editReferringProvider}
              onChange={(e) => setEditReferringProvider(e.target.value)}
              placeholder="e.g. Dr. Verma or Self"
            />

            <Select
              label="Communication Channel"
              value={editCommPreference}
              onChange={(e) => setEditCommPreference(e.target.value)}
              options={[
                { value: "email", label: "Email Notifications" },
                { value: "whatsapp", label: "WhatsApp Alerts" },
                { value: "sms", label: "SMS Texts" }
              ]}
            />

            <div className="flex flex-col gap-2 bg-slate-50 p-4 rounded-lg border border-slate-100 mt-2">
              <label className="text-xs font-black text-slate-800">Patient Consent Declarations</label>
              <div className="flex items-start gap-3.5 mt-2">
                <input
                  id="edit-consent-operational"
                  type="checkbox"
                  checked={editConsentOperational}
                  onChange={(e) => setEditConsentOperational(e.target.checked)}
                  className="w-4 h-4 text-teal-600 border-slate-300 rounded focus:ring-teal-500 mt-0.5"
                />
                <div className="flex flex-col">
                  <label htmlFor="edit-consent-operational" className="text-xs font-bold text-slate-800">
                    Operational Communication Consent *
                  </label>
                </div>
              </div>

              <div className="flex items-start gap-3.5 mt-2">
                <input
                  id="edit-consent-promotional"
                  type="checkbox"
                  checked={editConsentPromotional}
                  onChange={(e) => setEditConsentPromotional(e.target.checked)}
                  className="w-4 h-4 text-teal-600 border-slate-300 rounded focus:ring-teal-500 mt-0.5"
                />
                <div className="flex flex-col">
                  <label htmlFor="edit-consent-promotional" className="text-xs font-bold text-slate-800">
                    Promotional / Marketing Consent
                  </label>
                </div>
              </div>
            </div>

            {editFormError && (
              <div className="mt-2">
                <Toast type="error" text={editFormError} onClose={() => setEditFormError(null)} />
              </div>
            )}
          </form>
        </Modal>
      )}
    </div>
  );
}
