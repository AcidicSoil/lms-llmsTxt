"use client";

import { useState, FormEvent, useEffect, useRef } from "react";

interface TopicInputProps {
  onSubmit: (topic: string) => void;
  isLoading: boolean;
  variant?: "hero" | "compact";
  initialValue?: string;
}

export default function TopicInput({
  onSubmit,
  isLoading,
  variant = "compact",
  initialValue = "",
}: TopicInputProps) {
  const [topic, setTopic] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (variant === "hero" && inputRef.current) {
      inputRef.current.focus();
    }
  }, [variant]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (topic.trim() && !isLoading) {
      onSubmit(topic.trim());
    }
  };

  if (variant === "hero") {
    return (
      <form onSubmit={handleSubmit} className="w-full">
        <div className="relative flex items-center rounded-xl border border-zinc-200 bg-white shadow-sm transition-all duration-200 focus-within:border-zinc-400 focus-within:shadow-md">
          <svg
            className="ml-4 h-4 w-4 flex-shrink-0 text-zinc-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Supabase Auth, React Server Components, Postgres…"
            disabled={isLoading}
            className="flex-1 bg-transparent px-3 py-3.5 text-sm text-zinc-900 placeholder-zinc-400 outline-none disabled:cursor-not-allowed disabled:opacity-50"
          />
          <div className="flex-shrink-0 p-1.5">
            <button
              type="submit"
              disabled={isLoading || !topic.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all duration-150 hover:bg-zinc-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-zinc-900"
            >
              {isLoading ? (
                <>
                  <svg
                    className="h-3.5 w-3.5 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  Generating
                </>
              ) : (
                <>
                  <svg
                    className="h-3.5 w-3.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                  Generate
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Enter a topic…"
        disabled={isLoading}
        className="flex-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-900 placeholder-zinc-400 outline-none ring-0 transition-all duration-150 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 disabled:cursor-not-allowed disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={isLoading || !topic.trim()}
        className="flex items-center gap-1.5 rounded-md bg-zinc-900 px-4 py-1.5 text-sm font-medium text-white transition-all duration-150 hover:bg-zinc-700 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-zinc-900"
      >
        {isLoading ? (
          <>
            <svg
              className="h-3.5 w-3.5 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Generating
          </>
        ) : (
          <>
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            Generate
          </>
        )}
      </button>
    </form>
  );
}
