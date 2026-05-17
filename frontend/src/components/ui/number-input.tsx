"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { ChevronUp, ChevronDown } from "lucide-react"

interface NumberInputProps {
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
  className?: string
  disabled?: boolean
}

export function NumberInput({
  value,
  onChange,
  min = 0,
  max = Infinity,
  step = 1,
  className,
  disabled,
}: NumberInputProps) {
  const handleIncrement = React.useCallback(() => {
    const newValue = Math.min(max, value + step)
    onChange(newValue)
  }, [value, step, max, onChange])

  const handleDecrement = React.useCallback(() => {
    const newValue = Math.max(min, value - step)
    onChange(newValue)
  }, [value, step, min, onChange])

  const handleInputChange = React.useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const rawValue = e.currentTarget.value
      if (rawValue === "") {
        onChange(0)
        return
      }
      const parsed = Number.parseFloat(rawValue)
      if (!Number.isNaN(parsed)) {
        const clamped = Math.min(max, Math.max(min, parsed))
        onChange(clamped)
      }
    },
    [onChange, min, max]
  )

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "ArrowUp") {
        e.preventDefault()
        handleIncrement()
      } else if (e.key === "ArrowDown") {
        e.preventDefault()
        handleDecrement()
      }
    },
    [handleIncrement, handleDecrement]
  )

  return (
    <div
      className={cn(
        "flex h-7 items-center rounded-md border border-node-input-border bg-node-input overflow-hidden",
        className
      )}
    >
      <input
        type="number"
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        className={cn(
          "w-14 h-full flex-1 bg-muted text-node-foreground text-xs text-center border-0 focus:outline-none focus:ring-0 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        )}
      />
      <div className="flex flex-col h-full border-l ">
        <button
          type="button"
          onClick={handleIncrement}
          disabled={disabled || value >= max}
          aria-label="Increment"
          className={cn(
            "flex-1 flex items-center justify-center px-1 hover:bg-card cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-muted"
          )}
        >
          <ChevronUp className="size-3 text-node-foreground" />
        </button>
        <div className="h-px bg-border" />
        <button
          type="button"
          onClick={handleDecrement}
          disabled={disabled || value <= min}
          aria-label="Decrement"
          className={cn(
            "flex-1 flex items-center justify-center px-1 hover:bg-card cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-muted"
          )}
        >
          <ChevronDown className="size-3 text-node-foreground" />
        </button>
      </div>
    </div>
  )
}
