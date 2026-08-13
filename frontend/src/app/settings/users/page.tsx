"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
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
import { UserPlus, Search, Shield, UserX, UserCheck, Edit3, AlertCircle } from "lucide-react";

interface Branch {
  id: number;
  name: string;
}

interface UserRecord {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  role: string;
  status: string;
  branch_id: number | null;
  last_login_at: string | null;
  created_at: string;
}

export default function UsersManagementPage() {
  const { user: currentAdmin } = useAuth();
  
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Success and Error Notification Toasts
  const [toastSuccess, setToastSuccess] = useState<string | null>(null);
  const [toastError, setToastError] = useState<string | null>(null);

  // Create User Modal States
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("technician");
  const [branchId, setBranchId] = useState<number | "">("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Edit User Modal States
  const [activeEditUser, setActiveEditUser] = useState<UserRecord | null>(null);
  const [editName, setEditName] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editRole, setEditRole] = useState("technician");
  const [editStatus, setEditStatus] = useState("active");
  const [editBranchId, setEditBranchId] = useState<number | "">("");
  const [editPassword, setEditPassword] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editFormError, setEditFormError] = useState<string | null>(null);

  const fetchUsersAndBranches = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [usersData, branchesData] = await Promise.all([
        api.get<UserRecord[]>("/users"),
        api.get<Branch[]>("/branches")
      ]);
      setUsers(usersData);
      setBranches(branchesData);
    } catch (err: any) {
      setError(err.detail || "Failed to load user management records.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsersAndBranches();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) {
      setFormError("Please fill in all required fields.");
      return;
    }

    setFormError(null);
    setIsSubmitting(true);
    try {
      const payload = {
        name,
        email,
        phone: phone || null,
        password,
        role,
        branch_id: branchId === "" ? null : Number(branchId),
        organization_id: currentAdmin?.organization_id
      };

      await api.post("/users", payload);
      setToastSuccess("User successfully created!");
      setIsCreateModalOpen(false);

      // Reset form fields
      setName("");
      setEmail("");
      setPhone("");
      setPassword("");
      setRole("technician");
      setBranchId("");

      fetchUsersAndBranches();
    } catch (err: any) {
      setFormError(err.detail || "Failed to create user staff record.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeEditUser) return;

    setEditFormError(null);
    setIsEditing(true);
    try {
      const payload: any = {
        name: editName,
        phone: editPhone || null,
        role: editRole,
        status: editStatus,
        branch_id: editBranchId === "" ? null : Number(editBranchId)
      };

      if (editPassword) {
        payload.password = editPassword;
      }

      await api.patch(`/users/${activeEditUser.id}`, payload);
      setToastSuccess("User profile successfully updated!");
      setActiveEditUser(null);
      setEditPassword("");

      fetchUsersAndBranches();
    } catch (err: any) {
      setEditFormError(err.detail || "Failed to update user profile.");
    } finally {
      setIsEditing(false);
    }
  };

  const handleToggleDeactivate = async (u: UserRecord) => {
    try {
      if (u.status === "active") {
        await api.delete(`/users/${u.id}`);
        setToastSuccess(`User '${u.name}' has been deactivated.`);
      } else {
        await api.patch(`/users/${u.id}`, { status: "active" });
        setToastSuccess(`User '${u.name}' has been activated.`);
      }
      fetchUsersAndBranches();
    } catch (err: any) {
      setToastError(err.detail || "Failed to toggle user status.");
    }
  };

  const openEditModal = (u: UserRecord) => {
    setActiveEditUser(u);
    setEditName(u.name);
    setEditPhone(u.phone || "");
    setEditRole(u.role);
    setEditStatus(u.status);
    setEditBranchId(u.branch_id || "");
    setEditPassword("");
  };

  const filteredUsers = users.filter((u) => {
    const query = searchQuery.toLowerCase();
    return (
      u.name.toLowerCase().includes(query) ||
      u.email.toLowerCase().includes(query) ||
      u.role.toLowerCase().includes(query)
    );
  });

  // Calculate metrics based on users state
  const totalUsers = users.length;
  const activeUsers = users.filter(u => u.status === "active").length;
  const adminUsers = users.filter(u => u.role === "admin").length;
  const techUsers = users.filter(u => u.role === "technician").length;

  const metrics = [
    { label: "Total Staff", value: totalUsers, sub: "Registered accounts" },
    { label: "Active Access", value: activeUsers, sub: "Can authenticate" },
    { label: "Administrators", value: adminUsers, sub: "Full system config" },
    { label: "Technicians", value: techUsers, sub: "Operational testing" },
  ];

  const columns = [
    {
      header: "Staff Member",
      accessor: (row: UserRecord) => (
        <div className="flex flex-col">
          <span className="font-semibold text-slate-900">{row.name}</span>
          <span className="text-[11px] text-slate-500">{row.email}</span>
        </div>
      ),
    },
    {
      header: "System Role",
      accessor: (row: UserRecord) => {
        // Distinct visual style based on role
        const roleClasses: Record<string, string> = {
          admin: "bg-teal-50 text-teal-700 border-teal-200",
          reception: "bg-blue-50 text-blue-700 border-blue-200",
          technician: "bg-purple-50 text-purple-700 border-purple-200",
          reviewer: "bg-indigo-50 text-indigo-700 border-indigo-200"
        };
        return (
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border capitalize ${roleClasses[row.role] || "bg-slate-50 text-slate-700"}`}>
            {row.role}
          </span>
        );
      },
    },
    {
      header: "Laboratory Branch",
      accessor: (row: UserRecord) => {
        const branch = branches.find(b => b.id === row.branch_id);
        return <span className="text-xs font-semibold text-slate-600">{branch ? branch.name : "All Branches"}</span>;
      },
    },
    {
      header: "Status",
      accessor: (row: UserRecord) => <Badge status={row.status} />,
    },
    {
      header: "Last Login",
      accessor: (row: UserRecord) => (
        <span className="text-xs font-semibold text-slate-500">
          {row.last_login_at
            ? new Date(row.last_login_at).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
            : "Never logged in"}
        </span>
      ),
    },
    {
      header: "Actions",
      accessor: (row: UserRecord) => {
        const isSelf = currentAdmin?.id === row.id;
        return (
          <div className="flex items-center gap-2">
            <button
              onClick={() => openEditModal(row)}
              className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-teal-600 transition-colors"
              title="Edit Profile"
            >
              <Edit3 className="w-4 h-4" />
            </button>
            
            {!isSelf && (
              <button
                onClick={() => handleToggleDeactivate(row)}
                className={`p-1 hover:bg-slate-100 rounded transition-colors ${
                  row.status === "active"
                    ? "text-slate-400 hover:text-red-600"
                    : "text-slate-400 hover:text-emerald-600"
                }`}
                title={row.status === "active" ? "Deactivate User" : "Activate User"}
              >
                {row.status === "active" ? (
                  <UserX className="w-4 h-4" />
                ) : (
                  <UserCheck className="w-4 h-4" />
                )}
              </button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="flex flex-col gap-6 w-full animate-in fade-in duration-200">
      {/* Top action header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">Users & Access</h1>
          <p className="text-xs text-slate-500 font-semibold mt-1">
            Manage laboratory staff login access, assign role-based permissions, and restrict accounts.
          </p>
        </div>
        <Button
          variant="primary"
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 text-xs font-bold py-2.5 px-4 shadow-sm"
        >
          <UserPlus className="w-4 h-4" />
          <span>Add Staff Member</span>
        </Button>
      </div>

      {/* Toast Notifications */}
      {toastSuccess && (
        <Toast type="success" text={toastSuccess} onClose={() => setToastSuccess(null)} />
      )}
      {toastError && (
        <Toast type="error" text={toastError} onClose={() => setToastError(null)} />
      )}

      {/* Summary metrics widgets */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        {metrics.map((m, idx) => (
          <Card key={idx} className="p-5 border border-slate-200/80 shadow-sm">
            <span className="block text-[10px] uppercase font-bold text-slate-400 tracking-wider">{m.label}</span>
            <span className="block text-xl font-black text-slate-900 mt-1.5 tracking-tight">{m.value}</span>
            <span className="block text-[10px] text-slate-500 mt-1 font-semibold">{m.sub}</span>
          </Card>
        ))}
      </div>

      {/* Staff Registry Table */}
      <Card className="p-0 border border-slate-200/80 shadow-sm overflow-hidden">
        {/* Search header */}
        <div className="p-5 border-b border-slate-100 bg-slate-50/20">
          <div className="max-w-md">
            <Input
              type="text"
              placeholder="Search staff by name, email, or role..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              icon={<Search className="w-4 h-4 text-slate-400" />}
            />
          </div>
        </div>

        {error ? (
          <div className="p-12 text-center">
            <div className="w-12 h-12 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">Database Connection Issue</h3>
            <p className="text-xs text-slate-500 mt-2">{error}</p>
          </div>
        ) : (
          <Table
            columns={columns}
            data={filteredUsers}
            isLoading={isLoading}
            emptyMessage="No staff records match your query."
          />
        )}
      </Card>

      {/* Create User Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Add Staff Member"
        actions={
          <>
            <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" form="create-user-form" isLoading={isSubmitting}>
              Create User
            </Button>
          </>
        }
      >
        <form id="create-user-form" onSubmit={handleCreateUser} className="flex flex-col gap-4">
          <Input
            label="Name *"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Robert Smith"
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Email Address *"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. robert@vyoma.com"
              required
            />
            <Input
              label="Phone Number"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="e.g. +91 99999 88888"
            />
          </div>

          <Input
            label="Default Password *"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min. 6 characters"
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="System Role *"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              options={[
                { value: "admin", label: "Admin" },
                { value: "reception", label: "Reception" },
                { value: "technician", label: "Technician" },
                { value: "reviewer", label: "Reviewer" }
              ]}
            />
            <div className="w-full flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-700">Lab Branch</label>
              <select
                value={branchId}
                onChange={(e) => setBranchId(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full text-sm rounded-lg border border-slate-200 bg-white text-slate-900 outline-none px-3.5 py-2.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
              >
                <option value="">All Branches</option>
                {branches.map(b => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>
          </div>

          {formError && (
            <div className="mt-2">
              <Toast type="error" text={formError} onClose={() => setFormError(null)} />
            </div>
          )}
        </form>
      </Modal>

      {/* Edit User Modal */}
      {activeEditUser && (
        <Modal
          isOpen={true}
          onClose={() => setActiveEditUser(null)}
          title={`Edit Staff Profile: ${activeEditUser.name}`}
          actions={
            <>
              <Button variant="outline" onClick={() => setActiveEditUser(null)}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" form="edit-user-form" isLoading={isEditing}>
                Update Profile
              </Button>
            </>
          }
        >
          <form id="edit-user-form" onSubmit={handleUpdateUser} className="flex flex-col gap-4">
            <Input
              label="Name *"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              placeholder="e.g. Robert Smith"
              required
            />

            <Input
              label="Phone Number"
              type="tel"
              value={editPhone}
              onChange={(e) => setEditPhone(e.target.value)}
              placeholder="e.g. +91 99999 88888"
            />

            <div className="grid grid-cols-2 gap-4">
              <Select
                label="System Role *"
                value={editRole}
                onChange={(e) => setEditRole(e.target.value)}
                options={[
                  { value: "admin", label: "Admin" },
                  { value: "reception", label: "Reception" },
                  { value: "technician", label: "Technician" },
                  { value: "reviewer", label: "Reviewer" }
                ]}
              />
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

            <div className="w-full flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-slate-700">Lab Branch</label>
              <select
                value={editBranchId}
                onChange={(e) => setEditBranchId(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full text-sm rounded-lg border border-slate-200 bg-white text-slate-900 outline-none px-3.5 py-2.5 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-colors"
              >
                <option value="">All Branches</option>
                {branches.map(b => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>

            {/* Optional Reset Password */}
            <div className="mt-2 pt-2 border-t border-slate-100">
              <Input
                label="Change Password"
                type="password"
                value={editPassword}
                onChange={(e) => setEditPassword(e.target.value)}
                placeholder="Leave blank to keep current password"
              />
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
