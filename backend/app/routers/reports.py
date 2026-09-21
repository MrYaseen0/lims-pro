"""Report release and PDF generation/download routes."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.core.database import db
from app.core.deps import get_current_user, require_role
from app.core.config import REPORTS_DIR
from app.models.schemas import OrderStatus


router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/reports/{order_id}/release", response_model=dict)
async def release_report(order_id: str, current_user: dict = Depends(require_role("pathologist", "lab_manager", "admin"))):
    
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] != OrderStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Order must be approved before releasing report")
    
    await db.orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.REPORT_RELEASED,
                "report_released_at": datetime.now(timezone.utc).isoformat(),
                "report_released_by": current_user["id"]
            },
            "$push": {"status_history": {
                "status": OrderStatus.REPORT_RELEASED,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": current_user["id"]
            }}
        }
    )
    
    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return updated

@router.get("/reports/{order_id}", response_model=dict)
async def get_report(order_id: str, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0})
    
    return {
        "order": order,
        "patient": patient,
        "lab_name": "LIMS.Pro Diagnostic Laboratory",
        "lab_address": "123 Medical Center, Healthcare City",
        "lab_phone": "+1-234-567-8900",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.post("/reports/{order_id}/generate-pdf", response_model=dict)
async def generate_pdf_report(order_id: str, current_user: dict = Depends(get_current_user)):
    """Generate a PDF report for an order (order must be approved or released)"""
    from pdf_generator import generate_report_pdf, save_report_pdf
    
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only allow PDF generation for approved or released orders
    if order["status"] not in [OrderStatus.APPROVED, OrderStatus.REPORT_RELEASED]:
        raise HTTPException(status_code=400, detail="PDF can only be generated for approved or released orders")
    
    # Get patient info
    patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get samples for the order
    samples = await db.samples.find({"order_id": order_id}, {"_id": 0}).to_list(10)
    order["samples"] = samples
    
    # Get pathologist name if available
    pathologist_name = None
    for test in order.get("tests", []):
        result = test.get("result", {})
        if result.get("approved_by"):
            pathologist = await db.users.find_one({"id": result["approved_by"]}, {"_id": 0, "name": 1})
            if pathologist:
                pathologist_name = pathologist.get("name")
                break
    
    # Lab info
    lab_info = {
        'name': 'LIMS.Pro Diagnostic Laboratory',
        'address': '123 Medical Center, Healthcare City',
        'phone': '+1-234-567-8900',
        'email': 'info@lims.pro'
    }
    
    try:
        # Generate PDF
        pdf_buffer = generate_report_pdf(order, patient, pathologist_name, lab_info)
        
        # Save PDF to file
        filename = save_report_pdf(pdf_buffer, order["order_id"], str(REPORTS_DIR))
        
        # Store PDF reference in order
        pdf_url = f"/api/reports/{order_id}/download/{filename}"
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {
                "pdf_filename": filename,
                "pdf_generated_at": datetime.now(timezone.utc).isoformat(),
                "pdf_generated_by": current_user["id"]
            }}
        )
        
        logger.info(f"PDF generated for order {order_id}: {filename}")
        
        return {
            "message": "PDF generated successfully",
            "filename": filename,
            "download_url": pdf_url,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"PDF generation failed for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@router.get("/reports/{order_id}/download/{filename}")
async def download_pdf_report(order_id: str, filename: str, current_user: dict = Depends(get_current_user)):
    """Download a generated PDF report"""
    # Verify order exists and user has access
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify filename matches order's PDF
    if order.get("pdf_filename") != filename:
        raise HTTPException(status_code=404, detail="PDF not found for this order")
    
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        path=str(filepath),
        media_type="application/pdf",
        filename=f"LabReport_{order.get('order_id', order_id)}.pdf",
        headers={"Content-Disposition": f"attachment; filename=LabReport_{order.get('order_id', order_id)}.pdf"}
    )


@router.get("/reports/{order_id}/pdf-stream")
async def stream_pdf_report(order_id: str, current_user: dict = Depends(get_current_user)):
    """Generate and stream PDF without saving (for preview)"""
    from pdf_generator import generate_report_pdf
    
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] not in [OrderStatus.APPROVED, OrderStatus.REPORT_RELEASED]:
        raise HTTPException(status_code=400, detail="PDF can only be generated for approved or released orders")
    
    patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get samples
    samples = await db.samples.find({"order_id": order_id}, {"_id": 0}).to_list(10)
    order["samples"] = samples
    
    # Get pathologist name
    pathologist_name = None
    for test in order.get("tests", []):
        result = test.get("result", {})
        if result.get("approved_by"):
            pathologist = await db.users.find_one({"id": result["approved_by"]}, {"_id": 0, "name": 1})
            if pathologist:
                pathologist_name = pathologist.get("name")
                break
    
    lab_info = {
        'name': 'LIMS.Pro Diagnostic Laboratory',
        'address': '123 Medical Center, Healthcare City',
        'phone': '+1-234-567-8900',
        'email': 'info@lims.pro'
    }
    
    try:
        pdf_buffer = generate_report_pdf(order, patient, pathologist_name, lab_info)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=LabReport_{order.get('order_id', order_id)}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF streaming failed for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
