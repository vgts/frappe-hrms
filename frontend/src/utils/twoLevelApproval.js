/**
 * Two-level approval UI helpers (Leave, Permission, Regularization).
 * Prefer server `is_owner` from get_*_approval_details; fallback to user_id / Employee name.
 */

export function isDocumentOwner(sessionEmployee, approvalDetails, docEmployee) {
	if (!docEmployee || !sessionEmployee?.data) return false
	const d = approvalDetails?.data
	if (d && typeof d.is_owner === "boolean") return d.is_owner
	const uid = d?.employee_user_id
	if (uid) return sessionEmployee.data.user_id === uid
	return sessionEmployee.data.name === docEmployee
}

/** True when we can safely decide approver vs applicant (name match or approval-details API loaded). */
export function isApprovalOwnerContextReady(sessionEmployee, approvalDetails, docEmployee) {
	if (!docEmployee) return false
	if (sessionEmployee?.data?.name === docEmployee) return true
	return approvalDetails?.data != null
}
