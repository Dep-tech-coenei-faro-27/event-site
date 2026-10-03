import React from 'react';
interface PageHeaderProps {
    backgroundImage: string;
    children: React.ReactNode;
    className?: string,
    contentClassName?: string
};

export default function PageHeader({ 
    backgroundImage, 
    children, 
    className = "pt-[140px] pb-[240px]", 
    contentClassName = "" 
}: PageHeaderProps) {
    return (
        <header
            className={`relative bg-cover bg-center ${className}`}
            style={{
                backgroundImage: `
                    linear-gradient(
                        90deg,
                        rgba(5, 13, 33, 0.96) 0%,
                        rgba(5, 13, 33, 0.74) 56%,
                        rgba(5, 13, 33, 0.88) 100%
                    ),
                    url(${backgroundImage})
                `
            }}
        >
            <div className="absolute top-0 inset-x-0 h-[150px] bg-gradient-to-b from-azul-noite/100 to-transparent pointer-events-none"></div>

            <div className={`relative z-10 max-w-[1180px] mx-auto w-[calc(100%-28px)] md:w-[calc(100%-40px)] ${contentClassName}`}>
                {children}
            </div>
        </header>
    );
}