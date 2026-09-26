import { useState, useRef, useEffect } from 'react';

export default function FaqItem({ question, answer }: { question: string; answer: string }) {

    const [isOpen, setIsOpen] = useState(false);
    const contentRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (contentRef.current) {
            if (isOpen){
                contentRef.current.style.maxHeight = `${contentRef.current.scrollHeight}px`;
            }else{
                contentRef.current.style.maxHeight = '0px';
            }
    }}, [isOpen]);

    return (
        <div className="border border-gray-200 bg-white">
            <button type="button"
            className="w-full flex items-center justify-between p-5 text-left bg-white hover:bg-gray-50 transition-colors duration-200 focus:outline-none"
            onClick={() => setIsOpen((prev) => !prev)} aria-expanded={isOpen}
            >
                <span className=""> 
                    {question} 
                </span>
                <span className="">
                    +
                </span>
            </button>
      <div ref={contentRef} className="transition-all duration-300 ease-in-out overflow-hidden">
        <div className="p-5 pt-0">
          {answer}
        </div>
      </div>
    </div>
  );
}