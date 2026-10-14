"use client";
export function AssumptionControl({
  label,
  value,
  min,
  max,
  step,
  changed,
  onChange,
}: {
  label: string;
  value: string;
  min: number;
  max: number;
  step: number;
  changed: boolean;
  onChange: (value: string) => void;
}) {
  const number = Number(value),
    valid =
      value !== "" &&
      Number.isFinite(number) &&
      number >= min &&
      number <= max &&
      (step !== 1 || Number.isInteger(number));
  return (
    <div className="control">
      <label>
        {label}
        {changed && (
          <span className="changed-dot" aria-label="Changed from baseline">
            {" "}
            ●
          </span>
        )}
      </label>
      <div className="control-row">
        <input
          type="range"
          aria-label={`${label} slider`}
          min={min}
          max={max}
          step={step}
          value={valid ? number : min}
          onChange={(e) => onChange(e.target.value)}
        />
        <input
          type="number"
          aria-label={label}
          aria-invalid={!valid}
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
      {!valid ? (
        <small className="control-error" role="alert">
          Enter {step === 1 ? "a whole number" : "a number"} between {min} and{" "}
          {max}.
        </small>
      ) : (
        <small>
          {min} to {max}
          {label.includes("%") ? "%" : " days"}
        </small>
      )}
    </div>
  );
}
