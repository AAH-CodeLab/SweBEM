"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { MessageSquare, X, Star, Send, Loader2, CheckCircle } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/auth-context";

export default function FeedbackButton() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { user } = useAuth();

  // Hide on login page
  if (pathname === "/login" || pathname === "/") {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating === 0) {
      setError("Please select a rating");
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const { error: insertError } = await supabase
        .from("feedback")
        .insert({
          user_id: user?.id,
          user_email: user?.email,
          rating,
          message: message.trim() || null,
          page: window.location.pathname,
        });
      
      if (insertError) {
        setError(insertError.message);
      } else {
        setSubmitted(true);
        setTimeout(() => {
          setIsOpen(false);
          setSubmitted(false);
          setRating(0);
          setMessage("");
        }, 2000);
      }
    } catch (err) {
      setError("Failed to submit feedback");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setError(null);
    if (!submitted) {
      setRating(0);
      setMessage("");
    }
  };

  return (
    <>
      {/* Info icon above feedback button */}
      <div className="fixed bottom-24 right-6 z-50">
        <div className="relative group">
          <button
            onClick={() => setInfoOpen(true)}
            className="flex h-14 w-14 items-center justify-center rounded-full bg-orange-500 text-white shadow-lg hover:bg-orange-600 transition-all hover:scale-105 active:scale-95"
            aria-label="About this tool"
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="8" strokeWidth="3" />
              <line x1="12" y1="11" x2="12" y2="17" />
            </svg>
          </button>
          {/* Hover tooltip - just label */}
          <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block whitespace-nowrap rounded-lg bg-gray-800 text-white text-xs px-3 py-1.5 shadow-lg pointer-events-none">
            About the tool
            <div className="absolute top-full right-5 border-4 border-transparent border-t-gray-800"></div>
          </div>
        </div>
      </div>

      {/* Info Modal */}
      {infoOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setInfoOpen(false)} />
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-in fade-in zoom-in-95 duration-200 max-h-[80vh] overflow-y-auto">
            <button onClick={() => setInfoOpen(false)} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors">
              <X className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100">
                <svg viewBox="0 0 24 24" className="h-5 w-5 text-orange-500" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="8" strokeWidth="3" />
                  <line x1="12" y1="11" x2="12" y2="17" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">About the Tool</h3>
            </div>
            <p className="text-gray-600 text-sm leading-relaxed">
              This tool is developed as part of the COOLGEOHEAT II project (Interreg Öresund-Kattegat-Skagerrak, 2024–2026), contributing to Work Package 3 on building energy consumption, and builds on foundational work carried out under the Geothermica-supported THE CHANGE project.
            </p>
            <p className="text-gray-600 text-sm leading-relaxed mt-3">
              It addresses a core challenge in the planning of 5th generation district heating and cooling networks (5GDHC): accurately estimating the heating and cooling demand of buildings before a thermal network is constructed. Undersized or oversized networks lead to either supply failures or unnecessary costs — both of which erode the economic case for thermal network deployment.
            </p>
            <p className="text-gray-600 text-sm leading-relaxed mt-3">
              The tool uses physics-based EnergyPlus simulations calibrated to Swedish building stock across eight building types — Single-Family Homes, Multi-Family Dwellings, Offices, Hotels, Schools, Hospitals, Warehouses and Retail stores — and covers weather conditions across all major Swedish climate zones. Users can adjust key parameters including number of floors, total conditioned area, construction period, insulation levels, window-to-wall ratio, and infiltration, to reflect both existing and planned buildings.
            </p>
            <p className="text-gray-600 text-sm leading-relaxed mt-3">
              Outputs include annual heating and cooling demand, monthly energy profiles, and key building performance indicators, enabling planners, engineers, and energy communities to size thermal networks with confidence and evaluate the impact of building renovation on network design.
            </p>
            <p className="text-gray-600 text-sm leading-relaxed mt-3">
              The tool corresponds to Deliverable D2 of COOLGEOHEAT II, led by VIA University College in collaboration with Lund University and Umeå University.
            </p>
          </div>
        </div>
      )}

      {/* Floating Feedback Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-orange-500 text-white shadow-lg hover:bg-orange-600 transition-all hover:scale-105 active:scale-95"
        title="Send Feedback"
      >
        <MessageSquare className="h-6 w-6" />
      </button>

      {/* Modal Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={handleClose}
          />
          
          {/* Modal */}
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-in fade-in zoom-in-95 duration-200">
            {/* Close button */}
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>

            {submitted ? (
              /* Success State */
              <div className="text-center py-8">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 mx-auto mb-4">
                  <CheckCircle className="h-8 w-8 text-green-500" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Thank you!</h3>
                <p className="text-gray-500">Your feedback has been submitted.</p>
              </div>
            ) : (
              /* Form */
              <form onSubmit={handleSubmit}>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Send Feedback</h3>
                <p className="text-gray-500 text-sm mb-6">Help us improve the Building Energy Simulator</p>

                {/* Star Rating */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    How would you rate your experience?
                  </label>
                  <div className="flex gap-2 justify-center">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setRating(star)}
                        onMouseEnter={() => setHoverRating(star)}
                        onMouseLeave={() => setHoverRating(0)}
                        className="p-1 transition-transform hover:scale-110"
                      >
                        <Star
                          className={`h-8 w-8 transition-colors ${
                            star <= (hoverRating || rating)
                              ? "fill-yellow-400 text-yellow-400"
                              : "text-gray-300"
                          }`}
                        />
                      </button>
                    ))}
                  </div>
                  {rating > 0 && (
                    <p className="text-center text-sm text-gray-500 mt-2">
                      {rating === 1 && "Poor"}
                      {rating === 2 && "Fair"}
                      {rating === 3 && "Good"}
                      {rating === 4 && "Very Good"}
                      {rating === 5 && "Excellent"}
                    </p>
                  )}
                </div>

                {/* Message */}
                <div className="mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Additional comments (optional)
                  </label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Tell us what you think..."
                    rows={4}
                    className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-200 outline-none resize-none text-sm"
                  />
                </div>

                {/* Error */}
                {error && (
                  <p className="text-sm text-red-500 text-center mb-4 bg-red-50 p-2 rounded-lg">
                    {error}
                  </p>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-orange-500 text-white py-3 rounded-lg font-medium hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
                >
                  {loading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      <Send className="h-5 w-5" />
                      Submit Feedback
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
