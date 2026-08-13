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
  FlaskConical,
  Search,
  Plus,
  ListCollapse,
  AlertCircle,
  Eye,
  Edit3,
  Trash2,
  Settings,
  ShieldCheck,
  CheckCircle,
  ToggleLeft
} from "lucide-react";

interface TestParameter {
  id?: number;
  name: string;
  code: string;
  unit: string | null;
  data_type: string;
  reference_range: string | null;
  lower_limit: number | null;
  upper_limit: number | null;
  critical_low: number | null;
  critical_high: number | null;
  ref_gender?: string | null;
  ref_age_min?: number | null;
  ref_age_max?: number | null;
  ref_context?: string | null;
  display_order: number;
}

interface Test {
  id: number;
  code: string;
  name: string;
  category: string;
  description: string | null;
  price: string;
  status: string;
  parameters: TestParameter[];
  updated_at: string;
}

interface PaginatedResponse {
  items: Test[];
  total: number;
  page: number;
  page_size: number;
}

export default function TestsPage() {
  const { user } = useAuth();
  const router = useRouter();

  const [tests, setTests] = useState<Test[]>([]);
  const [totalTests, setTotalTests] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Search & filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Success and Error notifications
  const [toastSuccess, setToastSuccess] = useState<string | null>(null);
  const [toastError, setToastError] = useState<string | null>(null);

  // Create Test Form Modal States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Hematology");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [parameters, setParameters] = useState<TestParameter[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Edit Test Form Modal States
  const [activeEditTest, setActiveEditTest] = useState<Test | null>(null);
  const [editCode, setEditCode] = useState("");
  const [editName, setEditName] = useState("");
  const [editCategory, setEditCategory] = useState("Hematology");
  const [editDescription, setEditDescription] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [editStatus, setEditStatus] = useState("active");
  const [editParameters, setEditParameters] = useState<TestParameter[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editFormError, setEditFormError] = useState<string | null>(null);

  const fetchTests = async (page = 1, query = "", cat = "", stat = "") => {
    setIsLoading(true);
    setError(null);
    try {
      let url = `/tests?page=${page}&page_size=${pageSize}`;
      if (query) url += `&q=${encodeURIComponent(query)}`;
      if (cat) url += `&category=${encodeURIComponent(cat)}`;
      if (stat) url += `&status=${encodeURIComponent(stat)}`;

      const res = await api.get<PaginatedResponse>(url);
      setTests(res.items);
      setTotalTests(res.total);
      setCurrentPage(res.page);
    } catch (err: any) {
      setError(err.detail || "Failed to load test catalog records.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTests(1, searchQuery, categoryFilter, statusFilter);
  }, [searchQuery, categoryFilter, statusFilter]);

  const handleAddTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || !name || !price) {
      setFormError("Please fill in all required fields.");
      return;
    }

    // Validate parameters
    for (const p of parameters) {
      if (!p.name || !p.code) {
        setFormError("All test parameters require a name and unique code.");
        return;
      }
    }

    setFormError(null);
    setIsSubmitting(true);
    try {
      const payload = {
        code,
        name,
        category,
        description: description || null,
        price: parseFloat(price),
        organization_id: user?.organization_id,
        parameters: parameters.map(p => ({
          ...p,
          lower_limit: p.lower_limit === null || p.lower_limit === undefined ? null : Number(p.lower_limit),
          upper_limit: p.upper_limit === null || p.upper_limit === undefined ? null : Number(p.upper_limit),
          critical_low: p.critical_low === null || p.critical_low === undefined ? null : Number(p.critical_low),
          critical_high: p.critical_high === null || p.critical_high === undefined ? null : Number(p.critical_high),
          ref_age_min: p.ref_age_min === null || p.ref_age_min === undefined ? null : Number(p.ref_age_min),
          ref_age_max: p.ref_age_max === null || p.ref_age_max === undefined ? null : Number(p.ref_age_max),
        }))
      };

      await api.post("/tests", payload);
      setToastSuccess("Test catalog record successfully added!");
      setIsModalOpen(false);
      
      // Reset form fields
      setCode("");
      setName("");
      setCategory("Hematology");
      setDescription("");
      setPrice("");
      setParameters([]);

      fetchTests(1, searchQuery, categoryFilter, statusFilter);
    } catch (err: any) {
      setFormError(err.detail || "Failed to add test catalog record.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateTest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeEditTest) return;

    if (!editCode || !editName || !editPrice) {
      setEditFormError("Please fill in all required fields.");
      return;
    }

    // Validate parameters
    for (const p of editParameters) {
      if (!p.name || !p.code) {
        setEditFormError("All test parameters require a name and unique code.");
        return;
      }
    }

    setEditFormError(null);
    setIsEditing(true);
    try {
      const payload = {
        code: editCode,
        name: editName,
        category: editCategory,
        description: editDescription || null,
        price: parseFloat(editPrice),
        status: editStatus,
        parameters: editParameters.map(p => ({
          name: p.name,
          code: p.code,
          unit: p.unit || null,
          data_type: p.data_type,
          reference_range: p.reference_range || null,
          lower_limit: p.lower_limit === null || p.lower_limit === undefined ? null : Number(p.lower_limit),
          upper_limit: p.upper_limit === null || p.upper_limit === undefined ? null : Number(p.upper_limit),
          critical_low: p.critical_low === null || p.critical_low === undefined ? null : Number(p.critical_low),
          critical_high: p.critical_high === null || p.critical_high === undefined ? null : Number(p.critical_high),
          ref_gender: p.ref_gender || null,
          ref_age_min: p.ref_age_min === null || p.ref_age_min === undefined ? null : Number(p.ref_age_min),
          ref_age_max: p.ref_age_max === null || p.ref_age_max === undefined ? null : Number(p.ref_age_max),
          ref_context: p.ref_context || null,
          display_order: Number(p.display_order)
        }))
      };

      await api.patch(`/tests/${activeEditTest.id}`, payload);
      setToastSuccess("Test catalog config updated successfully!");
      setActiveEditTest(null);

      fetchTests(currentPage, searchQuery, categoryFilter, statusFilter);
    } catch (err: any) {
      setEditFormError(err.detail || "Failed to update test catalog config.");
    } finally {
      setIsEditing(false);
    }
  };

  const handleToggleDeactivate = async (t: Test) => {
    try {
      const nextStatus = t.status === "active" ? "inactive" : "active";
      await api.patch(`/tests/${t.id}`, { status: nextStatus });
      setToastSuccess(`Test '${t.code}' has been ${nextStatus === "active" ? "activated" : "deactivated"}.`);
      fetchTests(currentPage, searchQuery, categoryFilter, statusFilter);
    } catch (err: any) {
      setToastError(err.detail || "Failed to toggle test status.");
    }
  };

  const openEditModal = (t: Test) => {
    setActiveEditTest(t);
    setEditCode(t.code);
    setEditName(t.name);
    setEditCategory(t.category);
    setEditDescription(t.description || "");
    setEditPrice(t.price);
    setEditStatus(t.status);
    setEditParameters(t.parameters);
  };

  const addParameterRow = (isEdit: boolean) => {
    const newParam: TestParameter = {
      name: "",
      code: "",
      unit: "",
      data_type: "numeric",
      reference_range: "",
      lower_limit: null,
      upper_limit: null,
      critical_low: null,
      critical_high: null,
      ref_gender: null,
      ref_age_min: null,
      ref_age_max: null,
      ref_context: null,
      display_order: isEdit ? editParameters.length + 1 : parameters.length + 1
    };

    if (isEdit) {
      setEditParameters([...editParameters, newParam]);
    } else {
      setParameters([...parameters, newParam]);
    }
  };

  const removeParameterRow = (idx: number, isEdit: boolean) => {
    if (isEdit) {
      setEditParameters(editParameters.filter((_, i) => i !== idx));
    } else {
      setParameters(parameters.filter((_, i) => i !== idx));
    }
  };

  const updateParameterField = (idx: number, field: keyof TestParameter, val: any, isEdit: boolean) => {
    if (isEdit) {
      const copy = [...editParameters];
      copy[idx] = { ...copy[idx], [field]: val };
      setEditParameters(copy);
    } else {
      const copy = [...parameters];
      copy[idx] = { ...copy[idx], [field]: val };
      setParameters(copy);
    }
  };

  const columns = [
    {
      header: "Code",
      accessor: (row: Test) => (
        <span className="font-extrabold text-slate-800 tracking-wide">{row.code}</span>
      ),
    },
    {
      header: "Test Name",
      accessor: (row: Test) => (
        <div className="flex flex-col gap-0.5">
          <span className="font-bold text-slate-900">{row.name}</span>
          <span className="text-[10px] text-slate-500 font-medium line-clamp-1">
            {row.description || "No description configured"}
          </span>
        </div>
      ),
    },
    {
      header: "Category",
      accessor: (row: Test) => (
        <span className="text-xs font-bold text-slate-600 bg-slate-100/80 px-2 py-0.5 rounded border border-slate-200/20">
          {row.category}
        </span>
      ),
    },
    {
      header: "Parameters",
      accessor: (row: Test) => (
        <button
          onClick={() => router.push(`/tests/${row.id}`)}
          className="text-xs font-bold text-teal-600 hover:text-teal-700 flex items-center gap-1 hover:underline"
        >
          <ListCollapse className="w-3.5 h-3.5" />
          <span>{row.parameters.length} Parameters</span>
        </button>
      ),
    },
    {
      header: "Price",
      accessor: (row: Test) => (
        <span className="font-bold text-slate-900">₹{parseFloat(row.price).toFixed(2)}</span>
      ),
    },
    {
      header: "Status",
      accessor: (row: Test) => <Badge status={row.status} />,
    },
    {
      header: "Actions",
      accessor: (row: Test) => {
        const isAdmin = user?.role === "admin";
        return (
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push(`/tests/${row.id}`)}
              className="p-1.5 hover:bg-slate-100 rounded text-slate-500 hover:text-teal-600 transition-colors"
              title="View Catalog Details"
            >
              <Eye className="w-4 h-4" />
            </button>
            {isAdmin && (
              <>
                <button
                  onClick={() => openEditModal(row)}
                  className="p-1.5 hover:bg-slate-100 rounded text-slate-500 hover:text-teal-600 transition-colors"
                  title="Configure Test & Params"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleToggleDeactivate(row)}
                  className={`p-1.5 hover:bg-slate-100 rounded transition-colors ${
                    row.status === "active" ? "text-slate-400 hover:text-red-600" : "text-slate-400 hover:text-emerald-600"
                  }`}
                  title={row.status === "active" ? "Deactivate Test" : "Activate Test"}
                >
                  <ToggleLeft className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        );
      },
    },
  ];

  const totalPages = Math.ceil(totalTests / pageSize);
  const isAdmin = user?.role === "admin";

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Top action header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">Test Catalog</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Configure laboratory tests, register dynamic parameters list, set references, and edit pricing.
          </p>
        </div>
        {isAdmin && (
          <Button
            variant="primary"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 text-xs font-bold py-2.5 px-4 shadow-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Add Test Record</span>
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

      {/* Catalog Search & Filters Header */}
      <div className="flex flex-wrap items-center gap-4 bg-white p-4 border border-slate-200/80 rounded-xl shadow-sm">
        <div className="flex-1 min-w-[200px]">
          <Input
            type="text"
            placeholder="Search by test code, name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search className="w-4 h-4 text-slate-400" />}
          />
        </div>
        <div className="w-[180px]">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="w-full text-xs rounded-lg border border-slate-200 bg-white text-slate-900 outline-none px-3.5 py-2.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors font-semibold"
          >
            <option value="">All Categories</option>
            <option value="Hematology">Hematology</option>
            <option value="Biochemistry">Biochemistry</option>
            <option value="Diabetology">Diabetology</option>
            <option value="Clinical Pathology">Clinical Pathology</option>
            <option value="Microbiology">Microbiology</option>
            <option value="Serology">Serology</option>
            <option value="Immunology">Immunology</option>
          </select>
        </div>
        <div className="w-[140px]">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full text-xs rounded-lg border border-slate-200 bg-white text-slate-900 outline-none px-3.5 py-2.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors font-semibold"
          >
            <option value="">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
          </select>
        </div>
      </div>

      {/* Tests Catalog Table */}
      <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden flex flex-col">
        <Table
          columns={columns}
          data={tests}
          isLoading={isLoading}
          emptyMessage="No laboratory tests found. Add your first catalog test to begin configuration."
        />

        {/* Pagination controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-4 border-t border-slate-100 bg-slate-50/10">
            <span className="text-xs text-slate-500 font-semibold">
              Showing page {currentPage} of {totalPages} ({totalTests} total tests)
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => fetchTests(currentPage - 1, searchQuery, categoryFilter, statusFilter)}
                disabled={currentPage === 1 || isLoading}
                className="py-1.5 px-3 text-xs"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                onClick={() => fetchTests(currentPage + 1, searchQuery, categoryFilter, statusFilter)}
                disabled={currentPage === totalPages || isLoading}
                className="py-1.5 px-3 text-xs"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Add Test Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create Laboratory Test"
        actions={
          <>
            <Button variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" form="add-test-form" isLoading={isSubmitting}>
              Save Test Configuration
            </Button>
          </>
        }
      >
        <form id="add-test-form" onSubmit={handleAddTest} className="flex flex-col gap-5">
          <div className="text-slate-900 font-black text-sm border-b border-slate-100 pb-2">
            Base Test Configuration
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Test Code *"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. CBC"
              required
            />
            <Select
              label="Category *"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              options={[
                { value: "Hematology", label: "Hematology" },
                { value: "Biochemistry", label: "Biochemistry" },
                { value: "Diabetology", label: "Diabetology" },
                { value: "Clinical Pathology", label: "Clinical Pathology" },
                { value: "Microbiology", label: "Microbiology" },
                { value: "Serology", label: "Serology" },
                { value: "Immunology", label: "Immunology" }
              ]}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <Input
                label="Test Name *"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Complete Blood Count"
                required
              />
            </div>
            <Input
              label="Price (INR) *"
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="e.g. 350.00"
              required
            />
          </div>

          <Input
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Evaluation of red blood cells, white blood cells, and platelets"
          />

          <div className="text-slate-900 font-black text-sm border-b border-slate-100 pt-2 pb-2 flex items-center justify-between">
            <span>Test Parameters Configuration</span>
            <Button
              variant="outline"
              type="button"
              onClick={() => addParameterRow(false)}
              className="py-1 px-3 text-[10px] font-extrabold flex items-center gap-1 border-teal-200 text-teal-700 hover:bg-teal-50"
            >
              <Plus className="w-3 h-3" />
              <span>Add Parameter</span>
            </Button>
          </div>

          {parameters.length === 0 ? (
            <div className="text-center py-6 border-2 border-dashed border-slate-200 rounded-lg text-slate-400 font-semibold text-xs bg-slate-50/50">
              No parameters added. Click "Add Parameter" to configure reporting values.
            </div>
          ) : (
            <div className="flex flex-col gap-4 max-h-[300px] overflow-y-auto pr-1">
              {parameters.map((p, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col gap-3 relative animate-in slide-in-from-top-2 duration-150">
                  <button
                    type="button"
                    onClick={() => removeParameterRow(idx, false)}
                    className="absolute top-4 right-4 text-slate-400 hover:text-red-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>

                  <div className="grid grid-cols-3 gap-3 mr-6">
                    <div className="col-span-2">
                      <input
                        type="text"
                        placeholder="Parameter Name *"
                        value={p.name}
                        onChange={(e) => updateParameterField(idx, "name", e.target.value, false)}
                        className="w-full text-xs rounded border border-slate-200 bg-white px-2.5 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                        required
                      />
                    </div>
                    <input
                      type="text"
                      placeholder="Code *"
                      value={p.code}
                      onChange={(e) => updateParameterField(idx, "code", e.target.value.toUpperCase(), false)}
                      className="w-full text-xs rounded border border-slate-200 bg-white px-2.5 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-4 gap-3">
                    <input
                      type="text"
                      placeholder="Unit (e.g. g/dL)"
                      value={p.unit || ""}
                      onChange={(e) => updateParameterField(idx, "unit", e.target.value, false)}
                      className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                    />
                    <select
                      value={p.data_type}
                      onChange={(e) => updateParameterField(idx, "data_type", e.target.value, false)}
                      className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                    >
                      <option value="numeric">Numeric</option>
                      <option value="text">Text</option>
                      <option value="boolean">Boolean</option>
                      <option value="select">Dropdown Select</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Ref Text (e.g. 12-15)"
                      value={p.reference_range || ""}
                      onChange={(e) => updateParameterField(idx, "reference_range", e.target.value, false)}
                      className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                    />
                    <input
                      type="number"
                      placeholder="Display Order"
                      value={p.display_order}
                      onChange={(e) => updateParameterField(idx, "display_order", Number(e.target.value), false)}
                      className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                    />
                  </div>

                  <div className="grid grid-cols-4 gap-3 bg-white p-2.5 rounded border border-slate-100 text-[10px]">
                    <div className="flex flex-col gap-1">
                      <label className="font-bold text-slate-500">Lower Limit</label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Min val"
                        value={p.lower_limit === null ? "" : p.lower_limit}
                        onChange={(e) => updateParameterField(idx, "lower_limit", e.target.value === "" ? null : Number(e.target.value), false)}
                        className="border border-slate-200 px-2 py-1 rounded outline-none text-[10px]"
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="font-bold text-slate-500">Upper Limit</label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Max val"
                        value={p.upper_limit === null ? "" : p.upper_limit}
                        onChange={(e) => updateParameterField(idx, "upper_limit", e.target.value === "" ? null : Number(e.target.value), false)}
                        className="border border-slate-200 px-2 py-1 rounded outline-none text-[10px]"
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="font-bold text-rose-600">Critical Low</label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Alert Min"
                        value={p.critical_low === null ? "" : p.critical_low}
                        onChange={(e) => updateParameterField(idx, "critical_low", e.target.value === "" ? null : Number(e.target.value), false)}
                        className="border border-rose-100 bg-rose-50/20 px-2 py-1 rounded outline-none text-[10px] text-rose-600 font-bold"
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="font-bold text-rose-600">Critical High</label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="Alert Max"
                        value={p.critical_high === null ? "" : p.critical_high}
                        onChange={(e) => updateParameterField(idx, "critical_high", e.target.value === "" ? null : Number(e.target.value), false)}
                        className="border border-rose-100 bg-rose-50/20 px-2 py-1 rounded outline-none text-[10px] text-rose-600 font-bold"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {formError && (
            <div className="mt-2">
              <Toast type="error" text={formError} onClose={() => setFormError(null)} />
            </div>
          )}
        </form>
      </Modal>

      {/* Edit Test Modal */}
      {activeEditTest && (
        <Modal
          isOpen={true}
          onClose={() => setActiveEditTest(null)}
          title={`Configure Test: ${activeEditTest.code}`}
          actions={
            <>
              <Button variant="outline" onClick={() => setActiveEditTest(null)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" form="edit-test-form" isLoading={isEditing}>
                Update Configuration
              </Button>
            </>
          }
        >
          <form id="edit-test-form" onSubmit={handleUpdateTest} className="flex flex-col gap-5">
            <div className="text-slate-900 font-black text-sm border-b border-slate-100 pb-2">
              Base Test Details
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Test Code *"
                value={editCode}
                onChange={(e) => setEditCode(e.target.value.toUpperCase())}
                placeholder="e.g. CBC"
                required
              />
              <Select
                label="Category *"
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
                options={[
                  { value: "Hematology", label: "Hematology" },
                  { value: "Biochemistry", label: "Biochemistry" },
                  { value: "Diabetology", label: "Diabetology" },
                  { value: "Clinical Pathology", label: "Clinical Pathology" },
                  { value: "Microbiology", label: "Microbiology" },
                  { value: "Serology", label: "Serology" },
                  { value: "Immunology", label: "Immunology" }
                ]}
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <Input
                  label="Test Name *"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="e.g. Complete Blood Count"
                  required
                />
              </div>
              <Input
                label="Price (INR) *"
                type="number"
                step="0.01"
                value={editPrice}
                onChange={(e) => setEditPrice(e.target.value)}
                placeholder="e.g. 350.00"
                required
              />
            </div>

            <div className="grid grid-cols-3 gap-4 items-end">
              <div className="col-span-2">
                <Input
                  label="Description"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Provide test summary"
                />
              </div>
              <Select
                label="Status *"
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value)}
                options={[
                  { value: "active", label: "Active" },
                  { value: "inactive", label: "Inactive" }
                ]}
              />
            </div>

            <div className="text-slate-900 font-black text-sm border-b border-slate-100 pt-2 pb-2 flex items-center justify-between">
              <span>Test Parameters Configuration</span>
              <Button
                variant="outline"
                type="button"
                onClick={() => addParameterRow(true)}
                className="py-1 px-3 text-[10px] font-extrabold flex items-center gap-1 border-teal-200 text-teal-700 hover:bg-teal-50"
              >
                <Plus className="w-3 h-3" />
                <span>Add Parameter</span>
              </Button>
            </div>

            {editParameters.length === 0 ? (
              <div className="text-center py-6 border-2 border-dashed border-slate-200 rounded-lg text-slate-400 font-semibold text-xs bg-slate-50/50">
                No parameters added. Click "Add Parameter" to configure reporting values.
              </div>
            ) : (
              <div className="flex flex-col gap-4 max-h-[300px] overflow-y-auto pr-1">
                {editParameters.map((p, idx) => (
                  <div key={idx} className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 flex flex-col gap-3 relative animate-in slide-in-from-top-2 duration-150">
                    <button
                      type="button"
                      onClick={() => removeParameterRow(idx, true)}
                      className="absolute top-4 right-4 text-slate-400 hover:text-red-600 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>

                    <div className="grid grid-cols-3 gap-3 mr-6">
                      <div className="col-span-2">
                        <input
                          type="text"
                          placeholder="Parameter Name *"
                          value={p.name}
                          onChange={(e) => updateParameterField(idx, "name", e.target.value, true)}
                          className="w-full text-xs rounded border border-slate-200 bg-white px-2.5 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                          required
                        />
                      </div>
                      <input
                        type="text"
                        placeholder="Code *"
                        value={p.code}
                        onChange={(e) => updateParameterField(idx, "code", e.target.value.toUpperCase(), true)}
                        className="w-full text-xs rounded border border-slate-200 bg-white px-2.5 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-4 gap-3">
                      <input
                        type="text"
                        placeholder="Unit"
                        value={p.unit || ""}
                        onChange={(e) => updateParameterField(idx, "unit", e.target.value, true)}
                        className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                      />
                      <select
                        value={p.data_type}
                        onChange={(e) => updateParameterField(idx, "data_type", e.target.value, true)}
                        className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                      >
                        <option value="numeric">Numeric</option>
                        <option value="text">Text</option>
                        <option value="boolean">Boolean</option>
                        <option value="select">Dropdown Select</option>
                      </select>
                      <input
                        type="text"
                        placeholder="Ref range Text"
                        value={p.reference_range || ""}
                        onChange={(e) => updateParameterField(idx, "reference_range", e.target.value, true)}
                        className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                      />
                      <input
                        type="number"
                        placeholder="Display Order"
                        value={p.display_order}
                        onChange={(e) => updateParameterField(idx, "display_order", Number(e.target.value), true)}
                        className="w-full text-[11px] rounded border border-slate-200 bg-white px-2 py-1.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none font-semibold"
                      />
                    </div>

                    <div className="grid grid-cols-4 gap-3 bg-white p-2.5 rounded border border-slate-100 text-[10px]">
                      <div className="flex flex-col gap-1">
                        <label className="font-bold text-slate-500">Lower Limit</label>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Min val"
                          value={p.lower_limit === null ? "" : p.lower_limit}
                          onChange={(e) => updateParameterField(idx, "lower_limit", e.target.value === "" ? null : Number(e.target.value), true)}
                          className="border border-slate-200 px-2 py-1 rounded outline-none text-[10px]"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="font-bold text-slate-500">Upper Limit</label>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Max val"
                          value={p.upper_limit === null ? "" : p.upper_limit}
                          onChange={(e) => updateParameterField(idx, "upper_limit", e.target.value === "" ? null : Number(e.target.value), true)}
                          className="border border-slate-200 px-2 py-1 rounded outline-none text-[10px]"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="font-bold text-rose-600">Critical Low</label>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Alert Min"
                          value={p.critical_low === null ? "" : p.critical_low}
                          onChange={(e) => updateParameterField(idx, "critical_low", e.target.value === "" ? null : Number(e.target.value), true)}
                          className="border border-rose-100 bg-rose-50/20 px-2 py-1 rounded outline-none text-[10px] text-rose-600 font-bold"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="font-bold text-rose-600">Critical High</label>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Alert Max"
                          value={p.critical_high === null ? "" : p.critical_high}
                          onChange={(e) => updateParameterField(idx, "critical_high", e.target.value === "" ? null : Number(e.target.value), true)}
                          className="border border-rose-100 bg-rose-50/20 px-2 py-1 rounded outline-none text-[10px] text-rose-600 font-bold"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

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
