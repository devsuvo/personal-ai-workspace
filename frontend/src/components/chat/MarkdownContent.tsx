import 'katex/dist/katex.min.css';
import { Check, Copy } from 'lucide-react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import {
  oneDark,
  oneLight,
} from 'react-syntax-highlighter/dist/esm/styles/prism';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import type { ThemeMode } from '../../hooks/useTheme';

interface MarkdownContentProps {
  content: string;
  theme: ThemeMode;
}

function CodeBlock({
  language,
  code,
  theme,
}: {
  language: string;
  code: string;
  theme: ThemeMode;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border/80 bg-surface-hover/50 px-3.5 py-1.5 text-[11px] text-ink-secondary">
        <span className="font-mono">{language || 'text'}</span>
        <button
          type="button"
          onClick={() => void handleCopy()}
          className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-ink-secondary transition-colors hover:bg-surface hover:text-ink-primary"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-500" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || 'text'}
        style={theme === 'dark' ? oneDark : oneLight}
        customStyle={{
          margin: 0,
          padding: '0.875rem 1rem',
          fontSize: '0.8125rem',
          background: 'transparent',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

export function MarkdownContent({ content, theme }: MarkdownContentProps) {
  return (
    <div className="prose-workspace text-[15px] leading-relaxed text-ink-primary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const text = String(children).replace(/\n$/, '');
            const isBlock = Boolean(match) || text.includes('\n');
            if (isBlock) {
              return (
                <CodeBlock
                  language={match ? match[1] : 'text'}
                  code={text}
                  theme={theme}
                />
              );
            }
            return (
              <code
                {...props}
                className="rounded-md bg-surface px-1.5 py-0.5 font-mono text-[0.85em] text-ink-primary"
              >
                {children}
              </code>
            );
          },
          p({ children }) {
            return <p className="mb-3 last:mb-0">{children}</p>;
          },
          ul({ children }) {
            return <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>;
          },
          h1({ children }) {
            return <h1 className="mb-2 mt-4 text-xl font-semibold">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="mb-2 mt-4 text-lg font-semibold">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="mb-1.5 mt-3 text-base font-semibold">{children}</h3>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-3 border-l-2 border-accent/60 pl-3 text-ink-secondary">
                {children}
              </blockquote>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto rounded-xl border border-border">
                <table className="w-full border-collapse text-left text-xs">
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="border-b border-border bg-surface px-3 py-2 font-semibold text-ink-primary">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="border-b border-border/60 px-3 py-2 text-ink-secondary">
                {children}
              </td>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-accent underline underline-offset-2 hover:text-accent-hover"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
